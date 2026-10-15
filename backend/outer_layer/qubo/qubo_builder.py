from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from outer_layer.distance_matrix import haversine_km
from outer_layer.qubo.position_constraints import add_exactly_one_penalty
from outer_layer.qubo.position_variables import PositionVariables


@dataclass(frozen=True)
class PositionQubo:
    matrix: np.ndarray
    variables: PositionVariables
    penalty: float

    @property
    def variable_count(self) -> int:
        return self.matrix.shape[0]

    def energy(self, bitstring: list[int] | np.ndarray) -> float:
        values = np.asarray(bitstring, dtype=float)
        if values.shape != (self.variable_count,) or not np.isin(values, [0, 1]).all():
            raise ValueError("bitstring must contain one binary value per QUBO variable")
        upper = np.triu(self.matrix)
        return float(
            values @ np.diag(upper)
            + sum(
                upper[left, right] * values[left] * values[right]
                for left in range(self.variable_count)
                for right in range(left + 1, self.variable_count)
            )
        )


def build_position_qubo(
    customers: pd.DataFrame,
    warehouses: pd.DataFrame,
    distance_matrix: pd.DataFrame,
    *,
    penalty: float | None = None,
) -> PositionQubo:
    """Build a two-depot, position-encoded QUBO for one customer cluster."""
    if customers.empty:
        raise ValueError("A cluster must contain at least one customer")
    if len(warehouses) != 2:
        raise ValueError("Each cluster QUBO requires exactly two candidate warehouses")
    required_customers = {"customer_id", "lat", "lon"}
    required_warehouses = {"warehouse_id", "lat", "lon", "cost_per_km"}
    if not required_customers.issubset(customers.columns):
        raise ValueError(f"Customer data must contain {sorted(required_customers)}")
    if not required_warehouses.issubset(warehouses.columns):
        raise ValueError(f"Warehouse data must contain {sorted(required_warehouses)}")

    customer_ids = tuple(customers["customer_id"].astype(str))
    warehouse_ids = tuple(warehouses["warehouse_id"].astype(str))
    if any(customer not in distance_matrix.index or customer not in distance_matrix.columns
           for customer in customer_ids):
        raise ValueError("distance_matrix must contain every cluster customer on both axes")
    variables = PositionVariables(warehouse_ids, customer_ids, tuple(range(len(customer_ids))))
    matrix = np.zeros((variables.count, variables.count), dtype=float)
    travel_costs = [
        float(warehouse.cost_per_km) * max(
            haversine_km(
                float(warehouse.lat),
                float(warehouse.lon),
                float(customer.lat),
                float(customer.lon),
            )
            for customer in customers.itertuples()
        )
        for warehouse in warehouses.itertuples()
    ]
    chosen_penalty = (
        penalty
        if penalty is not None
        else max(1.0, 2.0 * (len(customer_ids) + 1) * max(travel_costs, default=1.0))
    )
    if chosen_penalty <= 0:
        raise ValueError("penalty must be positive")

    customer_rows = customers.set_index(customers["customer_id"].astype(str))
    warehouse_rows = warehouses.set_index(warehouses["warehouse_id"].astype(str))
    for warehouse in warehouse_ids:
        depot = warehouse_rows.loc[warehouse]
        rate = float(depot["cost_per_km"])
        for customer in customer_ids:
            row = customer_rows.loc[customer]
            index = variables.index(warehouse, customer, 0)
            matrix[index, index] += rate * haversine_km(
                float(depot["lat"]), float(depot["lon"]), float(row["lat"]), float(row["lon"])
            )
            last = variables.index(warehouse, customer, len(customer_ids) - 1)
            matrix[last, last] += rate * haversine_km(
                float(row["lat"]), float(row["lon"]), float(depot["lat"]), float(depot["lon"])
            )
        for position in range(len(customer_ids) - 1):
            for source in customer_ids:
                for target in customer_ids:
                    if source == target:
                        continue
                    left = variables.index(warehouse, source, position)
                    right = variables.index(warehouse, target, position + 1)
                    i, j = sorted((left, right))
                    matrix[i, j] += rate * float(distance_matrix.loc[source, target])

    for customer in customer_ids:
        indices = [
            variables.index(warehouse, customer, position)
            for warehouse in warehouse_ids
            for position in variables.positions
        ]
        add_exactly_one_penalty(matrix, indices, chosen_penalty)
    for position in variables.positions:
        indices = [
            variables.index(warehouse, customer, position)
            for warehouse in warehouse_ids
            for customer in customer_ids
        ]
        add_exactly_one_penalty(matrix, indices, chosen_penalty)
    for left_warehouse in warehouse_ids:
        for right_warehouse in warehouse_ids:
            if left_warehouse == right_warehouse:
                continue
            for left_position in variables.positions:
                for right_position in variables.positions:
                    if left_position == right_position:
                        continue
                    for left_customer in customer_ids:
                        for right_customer in customer_ids:
                            left = variables.index(left_warehouse, left_customer, left_position)
                            right = variables.index(right_warehouse, right_customer, right_position)
                            i, j = sorted((left, right))
                            matrix[i, j] += chosen_penalty
    return PositionQubo(matrix=matrix, variables=variables, penalty=chosen_penalty)
