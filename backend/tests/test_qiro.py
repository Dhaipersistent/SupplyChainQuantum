import numpy as np
import pytest

from inner_layer.qaoa_measurements import QaoaMeasurements
from inner_layer.qiro import fix_biased_variables
from inner_layer.reduced_qubo import ReducedQubo
from tests.test_qubo import build_four_customer_qubo


def test_qiro_fixes_variables_from_measured_spin_biases(monkeypatch):
    qubo = build_four_customer_qubo()
    seed = np.zeros(qubo.variable_count, dtype=int)
    for position, customer in enumerate(qubo.variables.customers):
        seed[qubo.variables.index("w1", customer, position)] = 1
    reduced = ReducedQubo.from_matrix(qubo.matrix)
    reference_spin = {index: 1 - 2 * bit for index, bit in enumerate(seed)}
    initial_energy = qubo.energy(seed)

    def measured(matrix, variable_ids, **kwargs):
        expectations = np.asarray([reference_spin[index] for index in variable_ids], dtype=float)
        correlations = np.outer(expectations, expectations)
        np.fill_diagonal(correlations, 1.0)
        return QaoaMeasurements(
            variable_ids=tuple(variable_ids),
            expectations=expectations,
            correlations=correlations,
            counts={"0" * len(variable_ids): 4},
            shots=4,
            expected_energy=0.0,
            parameters=(0.1, 0.2),
        )

    monkeypatch.setattr("inner_layer.qiro.sample_qaoa_expectations", measured)
    history = fix_biased_variables(
        reduced,
        target_variables=20,
        expectation_threshold=0.75,
    )

    assert len(history) == 12
    assert reduced.variable_count == 20
    assert all(row["fixed_value"] == seed[row["fixed_variable"]] for row in history)
    assert all(row["method"] == "qiro_quantum_spin_bias" for row in history)
    assert reduced.energy(reduced.project(seed)) == pytest.approx(initial_energy)
    assert np.array_equal(reduced.reconstruct(reduced.project(seed)), seed)


def test_qiro_uses_measured_pair_inference_when_no_spin_bias_passes(monkeypatch):
    reduced = ReducedQubo.from_matrix(np.zeros((3, 3)))

    def measured(matrix, variable_ids, **kwargs):
        return QaoaMeasurements(
            variable_ids=tuple(variable_ids),
            expectations=np.zeros(3),
            correlations=np.array(
                [[1.0, -0.8, 0.2], [-0.8, 1.0, 0.1], [0.2, 0.1, 1.0]]
            ),
            counts={"001": 2, "110": 2},
            shots=4,
            expected_energy=0.0,
            parameters=(0.1, 0.2),
        )

    monkeypatch.setattr("inner_layer.qiro.sample_qaoa_expectations", measured)
    history = fix_biased_variables(
        reduced,
        target_variables=2,
        expectation_threshold=0.7,
    )

    assert history[0]["method"] == "qiro_quantum_pair_inference"
    assert history[0]["correlation_value"] == pytest.approx(-0.8)
    assert history[0]["relation"] == "Zi = -Zj"
    assert reduced.variable_count == 2


def test_qiro_stops_instead_of_reducing_below_measurement_threshold(monkeypatch):
    reduced = ReducedQubo.from_matrix(np.zeros((2, 2)))

    def measured(matrix, variable_ids, **kwargs):
        return QaoaMeasurements(
            variable_ids=tuple(variable_ids),
            expectations=np.zeros(2),
            correlations=np.eye(2),
            counts={"00": 2},
            shots=2,
            expected_energy=0.0,
            parameters=(0.1, 0.2),
        )

    monkeypatch.setattr("inner_layer.qiro.sample_qaoa_expectations", measured)
    with pytest.raises(RuntimeError, match="no measured spin bias or pair correlation"):
        fix_biased_variables(
            reduced,
            target_variables=1,
            expectation_threshold=0.6,
        )
