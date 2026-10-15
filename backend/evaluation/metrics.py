from __future__ import annotations


def reduction_ratio(original_variables: int, reduced_variables: int) -> float:
    if original_variables < 0 or reduced_variables < 0:
        raise ValueError("Variable counts must be non-negative")
    if original_variables == 0:
        return 0.0
    return (original_variables - reduced_variables) / original_variables


def relative_gap(candidate_energy: float, reference_energy: float) -> float:
    if reference_energy == 0:
        return 0.0 if candidate_energy == 0 else float("inf")
    return (candidate_energy - reference_energy) / abs(reference_energy)
