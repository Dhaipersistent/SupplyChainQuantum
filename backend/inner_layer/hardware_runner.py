from __future__ import annotations

import numpy as np


def run_on_ibm_hardware(
    matrix: np.ndarray,
    warm_start_bits: list[int],
    *,
    parameters: list[float],
    simulator_validated: bool,
    explicit_opt_in: bool,
    shots: int = 1024,
) -> dict[str, object]:
    """Reject IBM submission until hardware execution is explicitly re-enabled."""
    upper = np.triu(np.asarray(matrix, dtype=float))
    variable_count = upper.shape[0]
    if upper.ndim != 2 or upper.shape[1] != variable_count:
        raise ValueError("QUBO matrix must be square")
    if variable_count == 0 or not np.isfinite(upper).all():
        raise ValueError("QUBO must have at least one variable and finite coefficients")
    if variable_count > 20:
        raise ValueError("IBM execution is limited to reduced QUBOs with at most 20 variables")
    if len(warm_start_bits) != variable_count or any(bit not in (0, 1) for bit in warm_start_bits):
        raise ValueError("warm_start_bits must match the reduced QUBO size")
    if not simulator_validated:
        raise RuntimeError("IBM execution is blocked until simulator validation succeeds")
    if not explicit_opt_in:
        raise RuntimeError("IBM execution requires explicit opt-in")
    if shots < 1:
        raise ValueError("shots must be positive")
    if not parameters or len(parameters) % 2:
        raise ValueError("parameters must contain gamma and beta values for each QAOA layer")
    raise RuntimeError("IBM hardware execution is disabled; use the Aer Simulator pipeline")
