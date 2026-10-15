"""
Unified Classical Optimizer (MILP)

This module replaces the previously separated Supplier Selection, Inventory Optimization, 
and Vehicle Routing Heuristics. It unifies them into a single Mixed-Integer Linear Program (MILP).

By solving these simultaneously, the model captures real-world correlations:
- We cannot route inventory from a warehouse if a supplier wasn't selected to deliver there.
- We cannot hold more inventory than warehouse storage allows.
- We cannot route out more units than the local vehicle fleet can carry.
- We cannot use routes that take longer than the customer's strict delivery deadline.

This creates a highly rigorous classical baseline to benchmark against Quantum/QAOA models.
"""

import pulp
import pandas as pd
import numpy as np

class UnifiedClassicalOptimizer:
    def __init__(self, suppliers_df: pd.DataFrame, warehouses_df: pd.DataFrame, customers_df: pd.DataFrame, routes_df: pd.DataFrame, vehicles_df: pd.DataFrame):
        """
        Initializes the optimization model by loading all supply chain entities 
        and pre-calculating the necessary penalty and cost matrices.
        """
        self.suppliers = suppliers_df.copy()
        self.warehouses = warehouses_df.copy()
        self.customers = customers_df.copy()
        self.vehicles = vehicles_df.copy()
        
        # Helper routines to structure our mathematical parameters
        self._prepare_route_parameters(routes_df)
        self._calculate_supplier_penalties()
        self._calculate_fleet_capacities()

    def _prepare_route_parameters(self, routes_df: pd.DataFrame):
        """
        Parses the physical routes between nodes into cost, time, and risk matrices.
        Converts bulk vehicle transport costs into per-unit transport costs.
        """
        # Assume an average truck carries 1000 units. We divide the total trip cost 
        # by this capacity to determine the routing cost per individual unit.
        TRUCK_CAPACITY = 1000.0
        
        self.dist_sw = {}  # Supplier -> Warehouse cost per unit
        self.dist_wc = {}  # Warehouse -> Customer cost per unit
        self.time_wc = {}  # Warehouse -> Customer travel time (hours)
        self.risk_wc = {}  # Warehouse -> Customer route risk penalty
        
        np.random.seed(42) # Ensure reproducible synthetic risk factors
        
        for r in routes_df.itertuples():
            per_unit_cost = (r.distance_km * r.cost_per_km) / TRUCK_CAPACITY
            
            # Map Supplier-to-Warehouse routes (First Leg)
            if r.from_node.startswith("S") and r.to_node.startswith("W"):
                self.dist_sw[(r.from_node, r.to_node)] = per_unit_cost
                
            # Map Warehouse-to-Customer routes (Second Leg)
            elif r.from_node.startswith("W") and r.to_node.startswith("C"):
                self.dist_wc[(r.from_node, r.to_node)] = per_unit_cost
                self.time_wc[(r.from_node, r.to_node)] = r.travel_time_hrs
                
                # Synthetic Route Risk Penalty: Longer distances are inherently riskier.
                # We add a $1 to $5 penalty per unit, scaled by the route distance.
                self.risk_wc[(r.from_node, r.to_node)] = (r.distance_km / 800.0) * np.random.uniform(1.0, 5.0) 

        # Apply massive penalty bounds (999.0) for impossible/non-existent routes
        # to prevent the optimizer from using paths that don't physically exist.
        for s in self.suppliers.itertuples():
            for w in self.warehouses.itertuples():
                if (s.supplier_id, w.warehouse_id) not in self.dist_sw:
                    self.dist_sw[(s.supplier_id, w.warehouse_id)] = 999.0
                    
        for w in self.warehouses.itertuples():
            for c in self.customers.itertuples():
                if (w.warehouse_id, c.customer_id) not in self.dist_wc:
                    self.dist_wc[(w.warehouse_id, c.customer_id)] = 999.0
                    self.time_wc[(w.warehouse_id, c.customer_id)] = 999.0
                    self.risk_wc[(w.warehouse_id, c.customer_id)] = 50.0

    def _calculate_supplier_penalties(self):
        """
        Incorporates multi-criteria scoring directly into the MILP objective.
        We normalize reliability, lead time, and capacity, converting them into 
        a financial penalty added to the cost of buying from a specific supplier.
        """
        max_rel = self.suppliers["reliability_score"].max() or 1.0
        max_lt = self.suppliers["lead_time_days"].max() or 1.0
        max_cap = self.suppliers["capacity"].max() or 1.0
        
        self.supplier_penalties = {}
        for s in self.suppliers.itertuples():
            # In an optimization minimization problem, LOWER costs/penalties are better.
            rel_penalty = (1.0 - (s.reliability_score / max_rel)) * 10.0  # High reliability = Low penalty
            lt_penalty  = (s.lead_time_days / max_lt) * 10.0              # Low lead time = Low penalty
            cap_penalty = (1.0 - (s.capacity / max_cap)) * 5.0            # High capacity = Low penalty
            
            # This combined penalty is added per-unit in the objective function
            self.supplier_penalties[s.supplier_id] = rel_penalty + lt_penalty + cap_penalty

    def _calculate_fleet_capacities(self):
        """
        Aggregates the total weight capacity of all vehicles stationed at each warehouse.
        Used to strictly bound the maximum outflow a warehouse can physically ship.
        """
        self.wh_fleet_capacity = {}
        for w in self.warehouses.itertuples():
            fleet = self.vehicles[self.vehicles["warehouse_id"] == w.warehouse_id]
            self.wh_fleet_capacity[w.warehouse_id] = fleet["capacity_kg"].sum()

    def optimize(self) -> dict:
        """
        Constructs and solves the Unified Mixed-Integer Linear Program.
        """
        prob = pulp.LpProblem("Unified_Supply_Chain_MILP", pulp.LpMinimize)
        
        # =====================================================================
        # 1. DECISION VARIABLES
        # =====================================================================
        
        # y_s: Binary variable indicating if Supplier 's' is selected for procurement (0 or 1).
        y = {s.supplier_id: pulp.LpVariable(f"y_{s.supplier_id}", cat="Binary") 
             for s in self.suppliers.itertuples()}
        
        # x_sw: Continuous variable for the number of units flowing from Supplier 's' to Warehouse 'w'.
        x = {(s.supplier_id, w.warehouse_id): pulp.LpVariable(f"x_{s.supplier_id}_{w.warehouse_id}", lowBound=0, cat="Continuous")
             for s in self.suppliers.itertuples() for w in self.warehouses.itertuples()}
             
        # z_wc: Continuous variable for the number of units flowing from Warehouse 'w' to Customer 'c'.
        z = {(w.warehouse_id, c.customer_id): pulp.LpVariable(f"z_{w.warehouse_id}_{c.customer_id}", lowBound=0, cat="Continuous")
             for w in self.warehouses.itertuples() for c in self.customers.itertuples()}
             
        # =====================================================================
        # 2. OBJECTIVE FUNCTION
        # =====================================================================
        
        # Leg 1 Cost (Supplier -> Warehouse): 
        # Raw unit cost + S->W transit cost + Warehouse holding cost + Supplier quality penalties
        obj_sw = pulp.lpSum(
            x[(s.supplier_id, w.warehouse_id)] * (
                s.cost_per_unit + 
                self.dist_sw[(s.supplier_id, w.warehouse_id)] + 
                w.holding_cost_per_unit +
                self.supplier_penalties[s.supplier_id]
            )
            for s in self.suppliers.itertuples() for w in self.warehouses.itertuples()
        )
        
        # Leg 2 Cost (Warehouse -> Customer):
        # W->C transit cost + Route risk penalty
        obj_wc = pulp.lpSum(
            z[(w.warehouse_id, c.customer_id)] * (
                self.dist_wc[(w.warehouse_id, c.customer_id)] +
                self.risk_wc[(w.warehouse_id, c.customer_id)]
            )
            for w in self.warehouses.itertuples() for c in self.customers.itertuples()
        )
        
        # Tell the solver to minimize the total combined cost of the network
        prob += obj_sw + obj_wc, "Minimize_Total_Network_Cost"
        
        # =====================================================================
        # 3. MATHEMATICAL CONSTRAINTS (Correlations)
        # =====================================================================
        
        # Constraint 1: Supplier Capacity Limits (Correlation: Selection <-> Flow)
        # A supplier can only provide inventory (x_sw) if it is officially selected (y_s = 1).
        # If y_s = 0, the right side becomes 0, forcing all flow from that supplier to be 0.
        for s in self.suppliers.itertuples():
            prob += pulp.lpSum(x[(s.supplier_id, w.warehouse_id)] for w in self.warehouses.itertuples()) <= s.capacity * y[s.supplier_id], f"Cap_{s.supplier_id}"
            
        # Constraint 2: Warehouse Constraints (Correlation: Inflow <-> Outflow)
        for w in self.warehouses.itertuples():
            inflow = pulp.lpSum(x[(s.supplier_id, w.warehouse_id)] for s in self.suppliers.itertuples())
            outflow = pulp.lpSum(z[(w.warehouse_id, c.customer_id)] for c in self.customers.itertuples())
            
            # 2a. Flow Conservation: A warehouse cannot ship out more than it receives from suppliers.
            prob += outflow <= inflow, f"FlowConserve_{w.warehouse_id}"
            
            # 2b. Storage Capacity: Inventory arriving cannot exceed physical shelf space.
            prob += inflow <= w.storage_capacity, f"StorageCap_{w.warehouse_id}"
            
            # 2c. Vehicle Fleet Capacity: Outbound shipping cannot exceed the local truck capacity.
            prob += outflow <= self.wh_fleet_capacity[w.warehouse_id], f"FleetCap_{w.warehouse_id}"
            
        # Constraint 3: Strict Customer Demand Satisfaction
        # The sum of all deliveries to a customer must exactly equal what they ordered.
        for c in self.customers.itertuples():
            prob += pulp.lpSum(z[(w.warehouse_id, c.customer_id)] for w in self.warehouses.itertuples()) == c.demand_units, f"Demand_{c.customer_id}"
            
        # Constraint 4: Delivery Deadlines (Strict Timeline Cutoff)
        # We prevent the solver from using any W->C route that takes longer than the customer's deadline.
        for w in self.warehouses.itertuples():
            for c in self.customers.itertuples():
                travel_days = self.time_wc[(w.warehouse_id, c.customer_id)] / 24.0
                if travel_days > c.delivery_deadline_days:
                    # Force the continuous flow variable for this specific route to exactly zero
                    prob += z[(w.warehouse_id, c.customer_id)] == 0, f"Deadline_{w.warehouse_id}_{c.customer_id}"

        # =====================================================================
        # 4. SOLVER EXECUTION & RESULTS PARSING
        # =====================================================================
        
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        status_str = pulp.LpStatus[prob.status]
        
        # Retrieve the final binary states to see which suppliers the algorithm picked
        selected_suppliers = [sid for sid, var in y.items() if pulp.value(var) > 0.5]
        total_cost = round(pulp.value(prob.objective), 2) if prob.status == pulp.LpStatusOptimal else 0.0
        
        shipment_plan = []
        supplier_cost = 0.0
        inventory_cost = 0.0
        vrp_cost = 0.0
        
        # Traverse the optimized continuous variables to build a human-readable shipment plan
        for c in self.customers.itertuples():
            for w in self.warehouses.itertuples():
                val_z = pulp.value(z[(w.warehouse_id, c.customer_id)])
                
                # If flow exists on this W->C route
                if val_z and val_z > 0.01:
                    
                    # Trace back to find the primary supplier that fed this warehouse
                    primary_supplier = "Unknown"
                    max_in = 0
                    for s in self.suppliers.itertuples():
                        val_x = pulp.value(x[(s.supplier_id, w.warehouse_id)])
                        if val_x and val_x > max_in:
                            max_in = val_x
                            primary_supplier = s.supplier_id
                    
                    # Calculate sub-costs for metrics breakdown
                    routing_cost_wc = (val_z * self.dist_wc[(w.warehouse_id, c.customer_id)])
                    risk_cost_wc = (val_z * self.risk_wc[(w.warehouse_id, c.customer_id)])
                    vrp_cost += (routing_cost_wc + risk_cost_wc)
                    
                    proc_cost = 0
                    if primary_supplier != "Unknown":
                        s_row = self.suppliers[self.suppliers['supplier_id'] == primary_supplier].iloc[0]
                        proc_cost = (val_z * float(s_row['cost_per_unit']))
                        supplier_cost += proc_cost
                        inventory_cost += (val_z * float(w.holding_cost_per_unit))
                    
                    # Append row to Final Shipment Plan
                    shipment_plan.append({
                        "source": primary_supplier,
                        "warehouse": w.warehouse_id,
                        "customer": c.customer_id,
                        "units": round(val_z, 1),
                        "cost": round(routing_cost_wc + risk_cost_wc + proc_cost, 2),
                        "delivery_time_hrs": round(self.time_wc[(w.warehouse_id, c.customer_id)] + 12, 1) # Assumes 12h warehouse processing
                    })
                    
        return {
            "status": status_str,
            "total_cost": total_cost,
            "supplier_cost": round(supplier_cost, 2),
            "inventory_cost": round(inventory_cost, 2),
            "vrp_cost": round(vrp_cost, 2),
            "selected_suppliers": selected_suppliers,
            "shipment_plan": shipment_plan
        }
