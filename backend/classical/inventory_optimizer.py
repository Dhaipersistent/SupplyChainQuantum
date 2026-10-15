"""
Inventory allocation optimiser using Linear Programming (PuLP / CBC).

Decision variable : x[s, w]  — units ordered from supplier s to warehouse w
Objective         : minimise (ordering cost + holding cost)
Constraints:
    - Total ordered >= total customer demand
    - Each supplier's shipments <= its capacity
    - Each warehouse's intake   <= its storage capacity
"""

import pandas as pd
import pulp


class InventoryOptimizer:

    def __init__(self,
                 suppliers_df:  pd.DataFrame,
                 warehouses_df: pd.DataFrame,
                 customers_df:  pd.DataFrame):
        self.suppliers     = suppliers_df
        self.warehouses    = warehouses_df
        self.total_demand  = int(customers_df["demand_units"].sum())

    # ------------------------------------------------------------------

    def optimize(self) -> dict:
        prob = pulp.LpProblem("Inventory_Allocation", pulp.LpMinimize)

        # Decision variables
        x = {
            (s.supplier_id, w.warehouse_id): pulp.LpVariable(
                f"x_{s.supplier_id}_{w.warehouse_id}", lowBound=0, cat="Continuous"
            )
            for s in self.suppliers.itertuples()
            for w in self.warehouses.itertuples()
        }

        # Objective
        prob += pulp.lpSum(
            x[(s.supplier_id, w.warehouse_id)] * (s.cost_per_unit + 0.5 * w.holding_cost_per_unit)
            for s in self.suppliers.itertuples()
            for w in self.warehouses.itertuples()
        ), "total_cost"

        # Constraint 1: demand satisfaction
        prob += (
            pulp.lpSum(x.values()) >= self.total_demand,
            "demand_satisfaction"
        )

        # Constraint 2: supplier capacity
        for s in self.suppliers.itertuples():
            prob += (
                pulp.lpSum(x[(s.supplier_id, w.warehouse_id)]
                           for w in self.warehouses.itertuples()) <= s.capacity,
                f"cap_supplier_{s.supplier_id}"
            )

        # Constraint 3: warehouse storage
        for w in self.warehouses.itertuples():
            prob += (
                pulp.lpSum(x[(s.supplier_id, w.warehouse_id)]
                           for s in self.suppliers.itertuples()) <= w.storage_capacity,
                f"cap_warehouse_{w.warehouse_id}"
            )

        # Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=0))

        # Extract allocations
        alloc = [
            {"supplier_id": s, "warehouse_id": w, "order_qty": round(pulp.value(var), 2)}
            for (s, w), var in x.items()
            if (pulp.value(var) or 0) > 0.01
        ]

        return {
            "status":        pulp.LpStatus[prob.status],
            "total_cost":    round(pulp.value(prob.objective), 2),
            "total_demand":  self.total_demand,
            "allocation_df": pd.DataFrame(alloc),
        }
