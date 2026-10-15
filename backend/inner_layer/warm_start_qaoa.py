from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from scipy.optimize import minimize


@dataclass(frozen=True)
class WarmStartResult:
    bitstring: list[int]
    energy: float
    runtime_seconds: float
    solver_name: str
    variable_count: int
    backend: str
    parameters: list[float]
    feasible: bool
    simulator_sample_feasible: bool


def run_warm_start_qaoa(
    matrix: np.ndarray,
    warm_start: np.ndarray,
    *,
    p: int = 1,
    maxiter: int = 30,
    shots: int = 1024,
    seed: int = 42,
    feasible_validator: Callable[[np.ndarray], bool] | None = None,
) -> WarmStartResult:
    """Run simulator QAOA initialized from a feasible classical assignment."""
    upper = np.triu(np.asarray(matrix, dtype=float))
    count = upper.shape[0]
    if upper.ndim != 2 or upper.shape[1] != count:
        raise ValueError("QUBO matrix must be square")
    if count == 0 or not np.isfinite(upper).all():
        raise ValueError("QUBO must have at least one variable and finite coefficients")
    if count > 20:
        raise ValueError("Warm Start QAOA is capped at 20 variables")
    initial = np.asarray(warm_start, dtype=int)
    if initial.shape != (count,) or not np.isin(initial, [0, 1]).all():
        raise ValueError("warm_start must contain one binary value per QUBO variable")
    if p < 1 or maxiter < 1 or shots < 1:
        raise ValueError("p, maxiter, and shots must be positive")
    started = time.perf_counter()

    basis = np.arange(1 << count, dtype=np.uint32)
    energy_table = np.zeros(1 << count, dtype=float)
    for left in range(count):
        energy_table += upper[left, left] * ((basis >> left) & 1)
        for right in range(left + 1, count):
            coefficient = upper[left, right]
            if abs(coefficient) < 1e-12:
                continue
            energy_table += coefficient * (((basis >> left) & 1) & ((basis >> right) & 1))

    cost_terms: list[tuple[tuple[int, ...], float]] = []
    linear = upper.diagonal().copy()
    for left in range(count):
        for right in range(left + 1, count):
            coefficient = upper[left, right]
            if abs(coefficient) < 1e-12:
                continue
            linear[left] += coefficient * 0.5
            linear[right] += coefficient * 0.5
            cost_terms.append(((left, right), float(coefficient * 0.25)))
    for index, coefficient in enumerate(linear):
        if abs(coefficient) > 1e-12:
            cost_terms.append(((index,), float(-coefficient * 0.5)))

    def build_state(parameters: np.ndarray) -> Statevector:
        circuit = QuantumCircuit(count)
        for index, bit in enumerate(initial):
            if bit:
                circuit.x(index)
        for layer in range(p):
            gamma = float(parameters[layer])
            beta = float(parameters[p + layer])
            for qubits, coefficient in cost_terms:
                if len(qubits) == 1:
                    circuit.rz(2 * gamma * coefficient, qubits[0])
                else:
                    left, right = qubits
                    circuit.cx(left, right)
                    circuit.rz(2 * gamma * coefficient, right)
                    circuit.cx(left, right)
            for index in range(count):
                circuit.rx(2 * beta, index)
        return Statevector.from_instruction(circuit)

    def objective(parameters: np.ndarray) -> float:
        state = build_state(parameters)
        return float(state.probabilities() @ energy_table)

    initial_parameters = np.random.default_rng(seed).uniform(-0.15, 0.15, size=2 * p)
    optimized = minimize(
        objective,
        initial_parameters,
        method="COBYLA",
        options={"maxiter": max(maxiter, 2 * p + 2), "rhobeg": 0.5},
    )
    state = build_state(optimized.x)
    probabilities = np.asarray(state.probabilities())
    measured = initial.copy()
    feasible = feasible_validator is None or feasible_validator(measured)
    simulator_sample_feasible = False
    best_energy = float(
        measured @ upper.diagonal()
        + sum(
            upper[left, right] * measured[left] * measured[right]
            for left in range(count)
            for right in range(left + 1, count)
        )
    )
    samples = np.random.default_rng(seed).choice(len(probabilities), size=shots, p=probabilities)
    for basis_state in samples:
        candidate = np.asarray(
            [(int(basis_state) >> index) & 1 for index in range(count)],
            dtype=int,
        )
        if feasible_validator is not None and not feasible_validator(candidate):
            continue
        simulator_sample_feasible = True
        candidate_energy = float(
            candidate @ upper.diagonal()
            + sum(
                upper[left, right] * candidate[left] * candidate[right]
                for left in range(count)
                for right in range(left + 1, count)
            )
        )
        if not feasible or candidate_energy < best_energy:
            measured = candidate
            best_energy = candidate_energy
            feasible = True
    return WarmStartResult(
        bitstring=measured.tolist(),
        energy=best_energy,
        runtime_seconds=time.perf_counter() - started,
        solver_name="warm_start_qaoa_statevector",
        variable_count=count,
        backend="statevector_simulator",
        parameters=np.asarray(optimized.x, dtype=float).tolist(),
        feasible=feasible,
        simulator_sample_feasible=simulator_sample_feasible,
    )
