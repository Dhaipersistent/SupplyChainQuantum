from __future__ import annotations

from typing import Any

import numpy as np

from inner_layer.qaoa_measurements import sample_qaoa_expectations
from inner_layer.reduced_qubo import ReducedQubo


def reduce_correlated_variables(
    qubo: ReducedQubo,
    target_variables: int,
    *,
    shots: int = 2048,
    seed: int = 42,
    optimizer_iterations: int = 4,
    qaoa_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Apply RQAOA pair-correlation substitutions estimated by shot-based QAOA."""
    if target_variables < 1:
        raise ValueError("RQAOA target_variables must be at least one")
    if target_variables > qubo.variable_count:
        raise ValueError("target_variables cannot exceed the current variable count")

    history: list[dict[str, Any]] = []
    parameters = (0.5, 0.5)
    while qubo.variable_count > target_variables:
        measurement = sample_qaoa_expectations(
            qubo.matrix,
            qubo.variable_ids,
            shots=shots,
            seed=seed + len(history),
            optimizer_iterations=optimizer_iterations if not history else 0,
            initial_parameters=parameters,
        )
        parameters = measurement.parameters
        if qaoa_history is not None:
            qaoa_history.append(
                {
                    "algorithm": "rqaoa",
                    "iteration": len(history) + 1,
                    "remaining_variables": qubo.variable_count,
                    "backend": measurement.backend,
                    "max_bond_dimension": measurement.max_bond_dimension,
                    "truncation_threshold": measurement.truncation_threshold,
                    "parameter_optimization": measurement.parameter_optimization,
                    "shots": measurement.shots,
                    "circuit_runs": measurement.circuit_runs,
                    "optimizer_evaluations": measurement.optimizer_evaluations,
                    "optimizer_shots": measurement.optimizer_shots,
                    "total_shots": measurement.total_shots,
                    "expected_energy": measurement.expected_energy,
                    "parameters": list(measurement.parameters),
                    "variable_ids": list(measurement.variable_ids),
                    "expectations": measurement.expectations.tolist(),
                    "correlation_matrix": measurement.correlations.tolist(),
                    "counts": measurement.counts,
                }
            )

        pair_values = abs(measurement.correlations)
        for index in range(len(pair_values)):
            pair_values[index, : index + 1] = 0.0
        pair_values[np.diag_indices_from(pair_values)] = -np.inf
        left, right = divmod(
            int(pair_values.argmax()), pair_values.shape[1]
        )
        correlation = float(measurement.correlations[left, right])
        relation = "Zi = Zj" if correlation >= 0 else "Zi = -Zj"
        kept_variable = int(qubo.variable_ids[left])
        eliminated_variable = int(qubo.variable_ids[right])
        previous_count = qubo.variable_count
        qubo.merge_variables(
            left,
            right,
            complement=correlation < 0,
            method="rqaoa_quantum_correlation",
        )
        step = qubo.history[-1]
        step.update(
            {
                "iteration": len(history) + 1,
                "remaining_variables": qubo.variable_count,
                "correlation_value": correlation,
                "eliminated_variable": eliminated_variable,
                "kept_variable": kept_variable,
                "relation": relation,
                "reduced_qubo_size": qubo.variable_count,
                "previous_qubo_size": previous_count,
                "shots": measurement.shots,
                "expectation_value_left": float(measurement.expectations[left]),
                "expectation_value_right": float(measurement.expectations[right]),
                "parameter_optimization": measurement.parameter_optimization,
                "circuit_runs": measurement.circuit_runs,
                "optimizer_evaluations": measurement.optimizer_evaluations,
                "optimizer_shots": measurement.optimizer_shots,
                "total_shots": measurement.total_shots,
            }
        )
        history.append(step.copy())
    return history


def estimate_correlation(matrix: np.ndarray, left: int, right: int) -> float:
    """Return a raw QAOA <ZiZj> estimate from one shot-based Aer run."""
    upper = np.triu(np.asarray(matrix, dtype=float))
    if upper.ndim != 2 or upper.shape[0] != upper.shape[1]:
        raise ValueError("matrix must be square")
    if not 0 <= left < len(upper) or not 0 <= right < len(upper):
        raise ValueError("variable indices must be within the QUBO")
    measurement = sample_qaoa_expectations(
        upper,
        tuple(range(len(upper))),
        shots=2048,
    )
    return float(measurement.correlations[left, right])
