from __future__ import annotations

import time

from inner_layer.backtracking import backtrack_exact
from inner_layer.reduced_qubo import ReducedQubo


def solve_qubo_baseline(qubo: ReducedQubo, *, max_variables: int = 16) -> dict[str, object]:
    """Small-instance exact classical baseline; not used as the primary pipeline."""
    started = time.perf_counter()
    bits, energy = backtrack_exact(
        qubo.energy,
        qubo.variable_count,
        max_variables=max_variables,
    )
    return {
        "solver_name": "exact_classical_backtracking",
        "energy": energy,
        "runtime_seconds": time.perf_counter() - started,
        "variable_count": qubo.variable_count,
        "bitstring": bits.tolist(),
    }
