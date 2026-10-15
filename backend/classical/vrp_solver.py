"""
Vehicle Routing Problem solver — nearest-neighbour heuristic + 2-opt improvement.

For each warehouse:
    1. Build a route for each available vehicle.
    2. Use nearest-neighbour to assign unvisited customers.
    3. Improve each route with 2-opt swaps.

Returns per-route cost, distance, and customer sequence.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin(np.radians(lat2 - lat1) / 2) ** 2
         + np.cos(phi1) * np.cos(phi2)
         * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def _route_distance(route: List[str], dist_matrix: dict) -> float:
    return sum(dist_matrix.get((route[i], route[i + 1]), 0)
               for i in range(len(route) - 1))


def _two_opt(route: List[str], dist_matrix: dict, max_iter: int = 100) -> List[str]:
    best = route[:]
    improved = True
    iteration = 0
    while improved and iteration < max_iter:
        improved = False
        iteration += 1
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                new_route = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                if _route_distance(new_route, dist_matrix) < _route_distance(best, dist_matrix):
                    best = new_route
                    improved = True
    return best


class VRPSolver:

    def __init__(self,
                 warehouses_df: pd.DataFrame,
                 customers_df:  pd.DataFrame,
                 vehicles_df:   pd.DataFrame,
                 routes_df:     pd.DataFrame):
        self.warehouses = warehouses_df
        self.customers  = customers_df
        self.vehicles   = vehicles_df
        self._build_dist_matrix(routes_df)

    def _build_dist_matrix(self, routes_df: pd.DataFrame):
        self.dist_matrix = {
            (r.from_node, r.to_node): r.distance_km
            for r in routes_df.itertuples()
        }
        # fill missing pairs by direct haversine
        all_nodes = pd.concat([
            self.warehouses[["warehouse_id", "lat", "lon"]].rename(columns={"warehouse_id": "id"}),
            self.customers[["customer_id",   "lat", "lon"]].rename(columns={"customer_id":  "id"}),
        ]).set_index("id")

        for n1 in all_nodes.index:
            for n2 in all_nodes.index:
                if n1 != n2 and (n1, n2) not in self.dist_matrix:
                    r1, r2 = all_nodes.loc[n1], all_nodes.loc[n2]
                    self.dist_matrix[(n1, n2)] = _haversine(r1.lat, r1.lon, r2.lat, r2.lon)

    # ------------------------------------------------------------------

    def solve(self) -> dict:
        all_routes, total_dist, total_cost = [], 0.0, 0.0
        unassigned = self.customers["customer_id"].tolist()

        for wh in self.warehouses.itertuples():
            depot = wh.warehouse_id
            vehicles_here = self.vehicles[self.vehicles["warehouse_id"] == depot]

            for veh in vehicles_here.itertuples():
                if not unassigned:
                    break

                # Nearest-neighbour construction
                route = [depot]
                load  = 0
                remaining = unassigned[:]

                while remaining:
                    current = route[-1]
                    nearest, best_d = None, float("inf")
                    for cid in remaining:
                        d = self.dist_matrix.get((current, cid), float("inf"))
                        cust = self.customers[self.customers["customer_id"] == cid].iloc[0]
                        if d < best_d and load + cust["demand_units"] <= veh.capacity_kg:
                            best_d, nearest = d, cid
                    if nearest is None:
                        break
                    route.append(nearest)
                    load += self.customers[self.customers["customer_id"] == nearest].iloc[0]["demand_units"]
                    remaining.remove(nearest)

                route.append(depot)

                # 2-opt improvement
                if len(route) > 3:
                    route = _two_opt(route, self.dist_matrix)

                dist = _route_distance(route, self.dist_matrix)
                cost = dist * veh.cost_per_km
                customers_served = [n for n in route if n.startswith("C")]

                if customers_served:
                    all_routes.append({
                        "vehicle_id":        veh.vehicle_id,
                        "warehouse_id":      depot,
                        "route":             " → ".join(route),
                        "customers_served":  len(customers_served),
                        "distance_km":       round(dist, 2),
                        "cost":              round(cost, 2),
                    })
                    total_dist += dist
                    total_cost += cost
                    for cid in customers_served:
                        if cid in unassigned:
                            unassigned.remove(cid)

        return {
            "routes_df":          pd.DataFrame(all_routes),
            "total_distance_km":  round(total_dist, 2),
            "total_cost":         round(total_cost, 2),
            "unserved_customers": unassigned,
        }
