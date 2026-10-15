from __future__ import annotations

import time

import numpy as np


def solve_qubo_gurobi(
    matrix: np.ndarray,
    *,
    time_limit_seconds: float = 30.0,
) -> dict[str, object]:
    """Solve a QUBO with Gurobi when its optional package and license are available."""
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as error:
        raise RuntimeError("Install the optional 'gurobipy' package to use Gurobi") from error
    upper = np.triu(np.asarray(matrix, dtype=float))
    if upper.ndim != 2 or upper.shape[0] != upper.shape[1]:
        raise ValueError("QUBO matrix must be square")
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    model = gp.Model("reduced_qubo")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit_seconds
    variables = model.addVars(upper.shape[0], vtype=GRB.BINARY, name="x")
    objective = gp.QuadExpr()
    for left in range(upper.shape[0]):
        objective.add(float(upper[left, left]) * variables[left])
        for right in range(left + 1, upper.shape[0]):
            if upper[left, right]:
                objective.add(float(upper[left, right]) * variables[left] * variables[right])
    model.setObjective(objective, GRB.MINIMIZE)
    started = time.perf_counter()
    model.optimize()
    runtime = time.perf_counter() - started
    if model.SolCount == 0:
        raise RuntimeError(f"Gurobi failed to find a solution (status={model.Status})")
    bits = [int(round(variables[index].X)) for index in range(upper.shape[0])]
    energy = float(
        sum(upper[i, i] * bits[i] for i in range(len(bits)))
        + sum(
            upper[i, j] * bits[i] * bits[j]
            for i in range(len(bits))
            for j in range(i + 1, len(bits))
        )
    )
    return {
        "solver_name": "gurobi",
        "status": int(model.Status),
        "energy": energy,
        "runtime_seconds": runtime,
        "variable_count": len(bits),
        "bitstring": bits,
    }
