from __future__ import annotations

from itertools import product

import numpy as np


def backtrack_exact(
    energy_function,
    variable_count: int,
    *,
    max_variables: int = 20,
) -> tuple[np.ndarray, float]:
    """Exact classical fallback for small reduced instances."""
    if variable_count < 0 or variable_count > max_variables:
        raise ValueError(f"Exact backtracking is limited to {max_variables} variables")
    best_bits: np.ndarray | None = None
    best_energy = float("inf")
    for candidate in product((0, 1), repeat=variable_count):
        bits = np.asarray(candidate, dtype=int)
        energy = float(energy_function(bits))
        if energy < best_energy:
            best_bits, best_energy = bits, energy
    if best_bits is None:
        raise RuntimeError("Backtracking did not evaluate any candidate")
    return best_bits, best_energy
