import numpy as np
import pytest

from inner_layer.qaoa_measurements import (
    QaoaMeasurements,
    qubo_to_ising,
    sample_qaoa_expectations,
)
from inner_layer.reduced_qubo import ReducedQubo
from inner_layer.rqaoa import reduce_correlated_variables
from tests.test_qubo import build_four_customer_qubo


def test_affine_reconstruction_preserves_energy_and_exposes_variable_map():
    matrix = np.array(
        [
            [1.5, -2.0, 0.5, 1.0],
            [0.0, 2.0, -1.0, 0.25],
            [0.0, 0.0, -0.5, 3.0],
            [0.0, 0.0, 0.0, 4.0],
        ]
    )
    reduced = ReducedQubo.from_matrix(matrix)
    reduced.merge_variables(0, 1, complement=True, method="test_complement")
    reduced.fix_variable(1, 1, method="test_fix")

    for assignment in np.ndindex(*(2,) * reduced.variable_count):
        active = np.asarray(assignment, dtype=int)
        original = reduced.reconstruct(active)
        assert reduced.energy(active) == pytest.approx(
            original @ np.diag(matrix)
            + sum(
                matrix[left, right] * original[left] * original[right]
                for left in range(len(original))
                for right in range(left + 1, len(original))
            )
        )
    assert len(reduced.reconstruction_map) == 4
    with pytest.raises(ValueError, match="binary"):
        reduced.reconstruct([0.5, 0])


def test_qubo_to_ising_preserves_energy_for_every_basis_assignment():
    matrix = np.array([[2.0, -3.0, 1.5], [0.0, -1.0, 0.25], [0.0, 0.0, 4.0]])
    constant, linear, pairs = qubo_to_ising(matrix)
    for bits in np.ndindex(2, 2, 2):
        values = np.asarray(bits, dtype=float)
        spins = 1 - 2 * values
        qubo_energy = values @ np.diag(matrix) + sum(
            matrix[left, right] * values[left] * values[right]
            for left in range(len(values))
            for right in range(left + 1, len(values))
        )
        ising_energy = constant + linear @ spins + sum(
            coefficient * spins[left] * spins[right]
            for left, right, coefficient in pairs
        )
        assert ising_energy == pytest.approx(qubo_energy)


def test_shot_qaoa_returns_measured_single_and_pair_expectations():
    result = sample_qaoa_expectations(
        np.array([[1.0, -2.0], [0.0, 1.0]]),
        (0, 1),
        shots=128,
        seed=7,
        optimizer_iterations=2,
    )

    assert result.shots == 128
    assert result.correlations.shape == (2, 2)
    assert np.allclose(result.correlations, result.correlations.T)
    assert np.allclose(result.expectations, result.correlations.diagonal())
    assert result.correlations[0, 0] == pytest.approx(1.0)
    assert sum(result.counts.values()) == 128


def test_rqaoa_selects_strongest_measured_pair_and_preserves_affine_energy(monkeypatch):
    qubo = build_four_customer_qubo()
    seed = np.zeros(qubo.variable_count, dtype=int)
    for position, customer in enumerate(qubo.variables.customers):
        seed[qubo.variables.index("w1", customer, position)] = 1
    reduced = ReducedQubo.from_matrix(qubo.matrix)
    initial_energy = qubo.energy(seed)
    calls = []

    def measured(matrix, variable_ids, **kwargs):
        calls.append(tuple(variable_ids))
        spins = np.asarray([1 - 2 * seed[index] for index in variable_ids])
        correlations = np.outer(spins, spins).astype(float) * 0.1
        np.fill_diagonal(correlations, 1.0)
        correlations[0, 1] = correlations[1, 0] = 0.93 * spins[0] * spins[1]
        correlations[0, 2] = correlations[2, 0] = 0.81 * spins[0] * spins[2]
        return QaoaMeasurements(
            variable_ids=tuple(variable_ids),
            expectations=np.zeros(len(variable_ids)),
            correlations=correlations,
            counts={"0" * len(variable_ids): 4},
            shots=4,
            expected_energy=0.0,
            parameters=(0.1, 0.2),
        )

    monkeypatch.setattr("inner_layer.rqaoa.sample_qaoa_expectations", measured)
    history = reduce_correlated_variables(reduced, target_variables=24)

    assert len(history) == len(calls) == 8
    assert reduced.variable_count == 24
    first_correlation = 0.93 * (1 - 2 * seed[0]) * (1 - 2 * seed[1])
    assert history[0]["correlation_value"] == pytest.approx(first_correlation)
    assert history[0]["relation"] == (
        "Zi = Zj" if first_correlation > 0 else "Zi = -Zj"
    )
    assert history[0]["reduced_qubo_size"] == 31
    assert reduced.energy(reduced.project(seed)) == pytest.approx(initial_energy)
    assert np.array_equal(reduced.reconstruct(reduced.project(seed)), seed)
    assert all(
        row["method"] == "rqaoa_quantum_correlation"
        for row in reduced.history
    )


def test_rqaoa_records_full_measured_correlation_matrices(monkeypatch):
    reduced = ReducedQubo.from_matrix(np.array([[0.0, -1.0], [0.0, 0.0]]))
    qaoa_history = []

    def measured(matrix, variable_ids, **kwargs):
        return QaoaMeasurements(
            variable_ids=tuple(variable_ids),
            expectations=np.array([0.0, 0.0]),
            correlations=np.array([[1.0, -0.75], [-0.75, 1.0]]),
            counts={"01": 5},
            shots=5,
            expected_energy=-0.5,
            parameters=(0.2, 0.3),
        )

    monkeypatch.setattr("inner_layer.rqaoa.sample_qaoa_expectations", measured)
    reduce_correlated_variables(
        reduced,
        target_variables=1,
        qaoa_history=qaoa_history,
    )

    assert qaoa_history[0]["correlation_matrix"] == [[1.0, -0.75], [-0.75, 1.0]]
    assert qaoa_history[0]["shots"] == 5
