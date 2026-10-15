from __future__ import annotations

import numpy as np

from outer_layer.qubo.qubo_builder import PositionQubo


def decode_solution(
    bitstring: list[int] | np.ndarray,
    qubo: PositionQubo,
) -> dict[str, object]:
    values = np.asarray(bitstring, dtype=int)
    if values.shape != (qubo.variable_count,) or not np.isin(values, [0, 1]).all():
        raise ValueError("bitstring must contain one binary value per QUBO variable")

    selected: dict[int, list[tuple[str, str]]] = {
        position: [] for position in qubo.variables.positions
    }
    for warehouse, customer, position in qubo.variables.names:
        if values[qubo.variables.index(warehouse, customer, position)]:
            selected[position].append((warehouse, customer))
    if any(len(assignments) != 1 for assignments in selected.values()):
        raise ValueError("Solution violates the one-customer-per-position constraint")
    chosen_warehouses = {assignments[0][0] for assignments in selected.values()}
    if len(chosen_warehouses) != 1:
        raise ValueError("Solution switches warehouses within a route")
    ordered = [selected[position][0] for position in qubo.variables.positions]
    customers = [customer for _, customer in ordered]
    if len(set(customers)) != len(qubo.variables.customers) or set(customers) != set(
        qubo.variables.customers
    ):
        raise ValueError("Solution does not visit each customer exactly once")
    return {
        "warehouse_id": ordered[0][0],
        "route": customers,
        "energy": qubo.energy(values),
        "feasible": True,
    }
