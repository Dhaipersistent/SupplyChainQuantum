from __future__ import annotations

import time

import numpy as np


def solve_qubo_cp_sat(
    matrix: np.ndarray,
    *,
    time_limit_seconds: float = 30.0,
) -> dict[str, object]:
    """Solve a QUBO with OR-Tools CP-SAT when the optional package is installed."""
    try:
        from ortools.sat.python import cp_model
    except ImportError as error:
        raise RuntimeError("Install the optional 'ortools' package to use CP-SAT") from error
    upper = np.triu(np.asarray(matrix, dtype=float))
    if upper.ndim != 2 or upper.shape[0] != upper.shape[1]:
        raise ValueError("QUBO matrix must be square")
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    scale = 1000
    model = cp_model.CpModel()
    variables = [model.new_bool_var(f"x_{index}") for index in range(upper.shape[0])]
    objective = []
    for left in range(len(variables)):
        diagonal = int(round(float(upper[left, left]) * scale))
        if diagonal:
            objective.append(diagonal * variables[left])
        for right in range(left + 1, len(variables)):
            coefficient = int(round(float(upper[left, right]) * scale))
            if not coefficient:
                continue
            product = model.new_bool_var(f"product_{left}_{right}")
            model.add(product <= variables[left])
            model.add(product <= variables[right])
            model.add(product >= variables[left] + variables[right] - 1)
            objective.append(coefficient * product)
    model.minimize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    started = time.perf_counter()
    status = solver.solve(model)
    runtime = time.perf_counter() - started
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"CP-SAT failed to find a solution (status={solver.status_name(status)})")
    bits = [int(solver.value(variable)) for variable in variables]
    energy = float(
        sum(upper[i, i] * bits[i] for i in range(len(bits)))
        + sum(
            upper[i, j] * bits[i] * bits[j]
            for i in range(len(bits))
            for j in range(i + 1, len(bits))
        )
    )
    return {
        "solver_name": "cp_sat",
        "status": solver.status_name(status),
        "energy": energy,
        "runtime_seconds": runtime,
        "variable_count": len(bits),
        "bitstring": bits,
    }
