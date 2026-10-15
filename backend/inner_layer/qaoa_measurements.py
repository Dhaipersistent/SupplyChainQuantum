from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from scipy.optimize import minimize

MPS_MAX_BOND_DIMENSION = 64
MPS_TRUNCATION_THRESHOLD = 1e-10


@dataclass(frozen=True)
class QaoaMeasurements:
    variable_ids: tuple[int, ...]
    expectations: np.ndarray
    correlations: np.ndarray
    counts: dict[str, int]
    shots: int
    expected_energy: float
    parameters: tuple[float, float]
    backend: str = "aer_matrix_product_state"
    max_bond_dimension: int = MPS_MAX_BOND_DIMENSION
    truncation_threshold: float = MPS_TRUNCATION_THRESHOLD
    parameter_optimization: str = "fixed_p1"
    circuit_runs: int = 1
    optimizer_evaluations: int = 0
    optimizer_shots: int = 0
    total_shots: int = 0


def _energy(matrix: np.ndarray, bits: np.ndarray) -> float:
    return float(
        bits @ np.diag(matrix)
        + sum(
            matrix[left, right] * bits[left] * bits[right]
            for left in range(len(bits))
            for right in range(left + 1, len(bits))
        )
    )


def qubo_to_ising(
    matrix: np.ndarray,
) -> tuple[float, np.ndarray, list[tuple[int, int, float]]]:
    """Convert x in {0,1} to spins z=1-2x, returning c + h·Z + J·ZZ."""
    upper = np.triu(np.asarray(matrix, dtype=float))
    if upper.ndim != 2 or upper.shape[0] != upper.shape[1] or upper.shape[0] == 0:
        raise ValueError("matrix must be a non-empty square QUBO")
    if not np.isfinite(upper).all():
        raise ValueError("matrix coefficients must be finite")
    constant = float(np.diag(upper).sum() / 2)
    linear = -np.diag(upper).copy() / 2
    pair_terms: list[tuple[int, int, float]] = []
    for left in range(len(upper)):
        for right in range(left + 1, len(upper)):
            coefficient = float(upper[left, right])
            if abs(coefficient) < 1e-12:
                continue
            constant += coefficient / 4
            linear[left] -= coefficient / 4
            linear[right] -= coefficient / 4
            pair_terms.append((left, right, coefficient / 4))
    return constant, linear, pair_terms


def _circuit(
    linear: np.ndarray,
    pair_terms: list[tuple[int, int, float]],
    gamma: float,
    beta: float,
) -> QuantumCircuit:
    count = len(linear)
    circuit = QuantumCircuit(count)
    circuit.h(range(count))
    for index, coefficient in enumerate(linear):
        if abs(coefficient) > 1e-12:
            circuit.rz(2 * gamma * coefficient, index)
    for left, right, coefficient in pair_terms:
        circuit.rzz(2 * gamma * coefficient, left, right)
    for index in range(count):
        circuit.rx(2 * beta, index)
    circuit.measure_all()
    return circuit


def sample_qaoa_expectations(
    matrix: np.ndarray,
    variable_ids: tuple[int, ...],
    *,
    shots: int = 2048,
    seed: int = 42,
    optimizer_iterations: int = 0,
    initial_parameters: tuple[float, float] = (0.5, 0.5),
) -> QaoaMeasurements:
    """Optimize one p=1 QAOA layer and estimate Z and ZZ from Aer shots."""
    upper = np.triu(np.asarray(matrix, dtype=float))
    if upper.ndim != 2 or upper.shape[0] != upper.shape[1] or upper.shape[0] == 0:
        raise ValueError("matrix must be a non-empty square QUBO")
    if not np.isfinite(upper).all():
        raise ValueError("matrix coefficients must be finite")
    if len(variable_ids) != upper.shape[0]:
        raise ValueError("variable_ids must identify every active QUBO variable")
    if shots < 1 or optimizer_iterations < 0:
        raise ValueError("shots must be positive and optimizer_iterations non-negative")
    if len(initial_parameters) != 2 or not np.isfinite(initial_parameters).all():
        raise ValueError("initial_parameters must contain finite gamma and beta values")

    count = upper.shape[0]
    _, linear, pair_terms = qubo_to_ising(upper)

    scale = max(
        1.0,
        float(np.max(np.abs(linear), initial=0.0)),
        max((abs(term[2]) for term in pair_terms), default=0.0),
    )
    normalized_linear = linear / scale
    normalized_pairs = [
        (left, right, coefficient / scale)
        for left, right, coefficient in pair_terms
    ]
    simulator = AerSimulator(
        method="matrix_product_state",
        matrix_product_state_max_bond_dimension=MPS_MAX_BOND_DIMENSION,
        matrix_product_state_truncation_threshold=MPS_TRUNCATION_THRESHOLD,
    )
    run_number = 0

    def run_circuit(gamma: float, beta: float, run_shots: int) -> dict[str, int]:
        nonlocal run_number
        circuit = _circuit(normalized_linear, normalized_pairs, gamma, beta)
        compiled = transpile(circuit, simulator, optimization_level=1)
        counts = simulator.run(
            compiled,
            shots=run_shots,
            seed_simulator=seed + run_number,
        ).result().get_counts()
        run_number += 1
        if not counts:
            raise RuntimeError("Aer returned no QAOA measurement counts")
        return {str(bits): int(frequency) for bits, frequency in counts.items()}

    objective_shots = 0
    if optimizer_iterations:
        objective_shots = min(shots, 512)

        def objective(parameters: np.ndarray) -> float:
            gamma, beta = (float(parameters[0]), float(parameters[1]))
            counts = run_circuit(gamma, beta, objective_shots)
            total_energy = 0.0
            total_count = 0
            for measured, frequency in counts.items():
                bits = np.fromiter(
                    (int(bit) for bit in measured.replace(" ", "")[::-1]),
                    dtype=int,
                    count=count,
                )
                if bits.shape != (count,):
                    raise RuntimeError("Aer returned a bitstring with an unexpected width")
                total_energy += _energy(upper, bits) * frequency
                total_count += frequency
            return total_energy / total_count

        optimized = minimize(
            objective,
            np.asarray(initial_parameters, dtype=float),
            method="COBYLA",
            options={"maxiter": max(optimizer_iterations, 4), "rhobeg": 0.25},
        )
        gamma, beta = (float(optimized.x[0]), float(optimized.x[1]))
        parameter_optimization = "shot_based_cobyla"
    else:
        gamma, beta = (float(initial_parameters[0]), float(initial_parameters[1]))
        parameter_optimization = "transferred_p1"
    counts = run_circuit(gamma, beta, shots)
    spins: list[np.ndarray] = []
    weights: list[int] = []
    measured_energy = 0.0
    measured_total = 0
    for measured, frequency in counts.items():
        bits = np.fromiter(
            (int(bit) for bit in measured.replace(" ", "")[::-1]),
            dtype=int,
            count=count,
        )
        if bits.shape != (count,):
            raise RuntimeError("Aer returned a bitstring with an unexpected width")
        spins.append(1 - 2 * bits)
        weights.append(frequency)
        measured_energy += _energy(upper, bits) * frequency
        measured_total += frequency

    spin_samples = np.asarray(spins, dtype=float)
    sample_weights = np.asarray(weights, dtype=float)
    correlations = (spin_samples.T * sample_weights) @ spin_samples / measured_total
    expectations = correlations.diagonal().copy()
    return QaoaMeasurements(
        variable_ids=tuple(variable_ids),
        expectations=expectations,
        correlations=correlations,
        counts=counts,
        shots=measured_total,
        expected_energy=float(measured_energy / measured_total),
        parameters=(gamma, beta),
        backend="aer_matrix_product_state",
        max_bond_dimension=MPS_MAX_BOND_DIMENSION,
        truncation_threshold=MPS_TRUNCATION_THRESHOLD,
        parameter_optimization=parameter_optimization,
        circuit_runs=run_number,
        optimizer_evaluations=max(0, run_number - 1),
        optimizer_shots=objective_shots,
        total_shots=measured_total + max(0, run_number - 1) * objective_shots,
    )
