from __future__ import annotations

from typing import Any

import numpy as np

from inner_layer.qaoa_measurements import sample_qaoa_expectations
from inner_layer.reduced_qubo import ReducedQubo


def fix_biased_variables(
    qubo: ReducedQubo,
    target_variables: int,
    *,
    expectation_threshold: float = 0.05,
    shots: int = 2048,
    seed: int = 142,
    optimizer_iterations: int = 4,
    qaoa_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Apply QIRO spin-bias/pair-correlation inference from Aer QAOA samples."""
    if target_variables < 0:
        raise ValueError("target_variables must be non-negative")
    if target_variables > qubo.variable_count:
        raise ValueError("target_variables cannot exceed the current variable count")
    if not 0.0 < expectation_threshold <= 1.0:
        raise ValueError("expectation_threshold must be in (0, 1]")

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
        iteration = len(history) + 1
        if qaoa_history is not None:
            qaoa_history.append(
                {
                    "algorithm": "qiro",
                    "iteration": iteration,
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

        strongest_bias = int(abs(measurement.expectations).argmax())
        bias = float(measurement.expectations[strongest_bias])
        previous_count = qubo.variable_count
        if abs(bias) >= expectation_threshold:
            variable = int(qubo.variable_ids[strongest_bias])
            fixed_value = 0 if bias > 0 else 1
            qubo.fix_variable(
                strongest_bias,
                fixed_value,
                method="qiro_quantum_spin_bias",
            )
            relation = "Zi = +1" if bias > 0 else "Zi = -1"
            step = qubo.history[-1]
            step.update(
                {
                    "iteration": iteration,
                    "remaining_variables": qubo.variable_count,
                    "expectation_value": bias,
                    "correlation_value": bias,
                    "eliminated_variable": variable,
                    "fixed_variable": variable,
                    "fixed_value": fixed_value,
                    "fixed_variables": [{"variable": variable, "value": fixed_value}],
                    "relation": relation,
                    "reduced_qubo_size": qubo.variable_count,
                    "previous_qubo_size": previous_count,
                    "shots": measurement.shots,
                    "parameter_optimization": measurement.parameter_optimization,
                    "circuit_runs": measurement.circuit_runs,
                    "optimizer_evaluations": measurement.optimizer_evaluations,
                    "optimizer_shots": measurement.optimizer_shots,
                    "total_shots": measurement.total_shots,
                }
            )
        else:
            if qubo.variable_count < 2:
                break
            pair_values = abs(measurement.correlations)
            for index in range(len(pair_values)):
                pair_values[index, : index + 1] = 0.0
            pair_values[np.diag_indices_from(pair_values)] = -np.inf
            left, right = divmod(int(pair_values.argmax()), pair_values.shape[1])
            correlation = float(measurement.correlations[left, right])
            if abs(correlation) < expectation_threshold:
                break
            kept_variable = int(qubo.variable_ids[left])
            eliminated_variable = int(qubo.variable_ids[right])
            qubo.merge_variables(
                left,
                right,
                complement=correlation < 0,
                method="qiro_quantum_pair_inference",
            )
            relation = "Zi = Zj" if correlation >= 0 else "Zi = -Zj"
            step = qubo.history[-1]
            step.update(
                {
                    "iteration": iteration,
                    "remaining_variables": qubo.variable_count,
                    "expectation_value": bias,
                    "correlation_value": correlation,
                    "eliminated_variable": eliminated_variable,
                    "kept_variable": kept_variable,
                    "fixed_variables": [],
                    "relation": relation,
                    "reduced_qubo_size": qubo.variable_count,
                    "previous_qubo_size": previous_count,
                    "shots": measurement.shots,
                    "parameter_optimization": measurement.parameter_optimization,
                    "circuit_runs": measurement.circuit_runs,
                    "optimizer_evaluations": measurement.optimizer_evaluations,
                    "optimizer_shots": measurement.optimizer_shots,
                    "total_shots": measurement.total_shots,
                }
            )
        history.append(step.copy())

    if qubo.variable_count > target_variables:
        raise RuntimeError(
            "QIRO could not reach the requested size: no measured spin bias or pair "
            f"correlation met threshold {expectation_threshold:g} "
            f"({qubo.variable_count} variables remain)"
        )
    return history
