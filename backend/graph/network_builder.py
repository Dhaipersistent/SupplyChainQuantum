"""
Builds and queries the supply chain NetworkX graph.

Node types : "supplier" | "warehouse" | "customer"
Edge attrs  : distance (km), cost (total), travel_time (hrs)
"""

import pandas as pd
import networkx as nx
import numpy as np


class SupplyChainGraph:
    """Directed weighted graph over all supply-chain nodes."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.G: nx.DiGraph = nx.DiGraph()
        self._load_data()
        self._build_graph()

    def _load_data(self):
        d = self.data_dir
        self.suppliers  = pd.read_csv(f"{d}/suppliers.csv")
        self.warehouses = pd.read_csv(f"{d}/warehouses.csv")
        self.vehicles   = pd.read_csv(f"{d}/vehicles.csv")
        self.customers  = pd.read_csv(f"{d}/customers.csv")
        self.routes     = pd.read_csv(f"{d}/routes.csv")
        self.inventory  = pd.read_csv(f"{d}/inventory.csv")

    def _build_graph(self):
        # --- Supplier nodes ---
        for r in self.suppliers.itertuples():
            self.G.add_node(r.supplier_id,
                            type="supplier",
                            lat=r.lat, lon=r.lon,
                            capacity=r.capacity,
                            cost_per_unit=r.cost_per_unit,
                            lead_time=r.lead_time_days,
                            reliability=r.reliability_score)

        # --- Warehouse nodes ---
        for r in self.warehouses.itertuples():
            self.G.add_node(r.warehouse_id,
                            type="warehouse",
                            lat=r.lat, lon=r.lon,
                            storage_capacity=r.storage_capacity,
                            holding_cost=r.holding_cost_per_unit)

        # --- Customer nodes ---
        for r in self.customers.itertuples():
            self.G.add_node(r.customer_id,
                            type="customer",
                            lat=r.lat, lon=r.lon,
                            demand=r.demand_units,
                            priority=r.priority,
                            deadline=r.delivery_deadline_days)

        # --- Edges from routes ---
        for r in self.routes.itertuples():
            self.G.add_edge(r.from_node, r.to_node,
                            distance=r.distance_km,
                            cost=r.distance_km * r.cost_per_km,
                            travel_time=r.travel_time_hrs)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def nodes_by_type(self, node_type: str) -> list:
        return [n for n, d in self.G.nodes(data=True) if d.get("type") == node_type]

    def shortest_path(self, source: str, target: str):
        try:
            path = nx.shortest_path(self.G, source, target, weight="cost")
            cost = nx.shortest_path_length(self.G, source, target, weight="cost")
            return path, round(cost, 2)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, float("inf")

    def summary(self) -> dict:
        return {
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
            "suppliers":   len(self.nodes_by_type("supplier")),
            "warehouses":  len(self.nodes_by_type("warehouse")),
            "customers":   len(self.nodes_by_type("customer")),
            "total_demand": int(self.customers["demand_units"].sum()),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_node_positions(self) -> dict:
        """lon/lat positions keyed by node id for plotting."""
        return {n: (d["lon"], d["lat"]) for n, d in self.G.nodes(data=True)}
