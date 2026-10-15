import json

import numpy as np
import pandas as pd

from inner_layer.reduced_qubo import ReducedQubo
from inner_layer.qaoa_measurements import QaoaMeasurements
from inner_layer.warm_start_qaoa import WarmStartResult
from outer_layer.improvement_loop import _measure_reduced_energies, run_improvement_loop


def test_four_customer_pipeline_reduces_32_variables_before_qaoa(monkeypatch, tmp_path):
    customers = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3", "c4"],
            "lat": [0.0, 0.1, 0.2, 0.3],
            "lon": [0.0, 0.1, 0.2, 0.3],
        }
    )
    warehouses = pd.DataFrame(
        {
            "warehouse_id": ["w1", "w2"],
            "lat": [1.0, -1.0],
            "lon": [1.0, -1.0],
            "storage_capacity": [1000, 1000],
        }
    )
    vehicles = pd.DataFrame(
        {
            "vehicle_id": ["v1", "v2"],
            "warehouse_id": ["w1", "w2"],
            "cost_per_km": [1.0, 1.2],
        }
    )

    def fake_qaoa(matrix, warm_start, *, feasible_validator, maxiter, shots):
        feasible = feasible_validator(warm_start)
        return WarmStartResult(
            bitstring=warm_start.tolist(),
            energy=ReducedQubo.from_matrix(matrix).energy(warm_start),
            runtime_seconds=0.01,
            solver_name="test_warm_start_qaoa",
            variable_count=len(warm_start),
            backend="test_simulator",
            parameters=[0.1, 0.2],
            feasible=feasible,
            simulator_sample_feasible=feasible,
        )

    reference_bits = {}

    def fake_seed(variables, warehouse, ordered_customers):
        bits = np.zeros(variables.count, dtype=int)
        for position, customer in enumerate(ordered_customers):
            bits[variables.index(variables.warehouses[0], customer, position)] = 1
        reference_bits.update(enumerate(bits.tolist()))
        return bits

    def fake_measurement(matrix, variable_ids, **kwargs):
        spins = np.asarray([1 - 2 * reference_bits[index] for index in variable_ids])
        return QaoaMeasurements(
            variable_ids=tuple(variable_ids),
            expectations=spins.astype(float),
            correlations=np.outer(spins, spins).astype(float),
            counts={"0" * len(variable_ids): 1},
            shots=1,
            expected_energy=0.0,
            parameters=(0.1, 0.2),
        )

    monkeypatch.setattr("outer_layer.improvement_loop._make_seed", fake_seed)
    monkeypatch.setattr("inner_layer.rqaoa.sample_qaoa_expectations", fake_measurement)
    monkeypatch.setattr("outer_layer.improvement_loop.run_warm_start_qaoa", fake_qaoa)
    expected_artifacts = {
        "results.json",
        "assignments.json",
        "reduction_history.json",
        "qaoa_history.json",
        "experiment_log.json",
    }
    for artifact_name in expected_artifacts:
        (tmp_path / artifact_name).write_text('[{"legacy": true}]', encoding="utf-8")
    output = run_improvement_loop(
        customers,
        warehouses,
        vehicles,
        n_clusters=1,
        target_variables=20,
        output_dir=tmp_path,
    )

    record = output["results"][0]
    assert record["variable_count"] == 32
    assert record["reduced_variable_count"] == 20
    assert record["original_qubo_size"] == 32
    assert record["reduced_qubo_size"] == 20
    assert record["variables_removed"] == 12
    assert record["reduction_percentage"] == 37.5
    assert record["warehouse_count"] == 2
    assert record["position_count"] == 4
    assert record["hardware_eligible"] is True
    assert record["result"]["solver_sample_feasible"] is True
    assert record["result"]["route_distance_km"] > 0
    assert record["result"]["travel_cost"] > 0
    assert len(record["feedback_history"]) == 2
    assert [row["reduced_variable_count"] for row in output["reduction_history"]][-1] == 20
    assert [32] + [row["remaining_variables"] for row in output["reduction_history"]] == list(
        range(32, 19, -1)
    )
    for step in output["reduction_history"]:
        assert step["correlation_value"] is not None
        assert step["removed_variable"] == step["eliminated_variable"]
        assert step["relation"] in {"Zi = Zj", "Zi = -Zj"}
        assert step["variables_before"] == step["variable_count"]
        assert step["variables_after"] == step["remaining_variables"]
        assert step["reduced_qubo_energy"] is not None
        assert step["remaining_variables"] == step["reduced_variable_count"]
        assert step["qaoa_call_count"] == step["iteration"]
        assert step["aer_circuit_runs"] >= step["qaoa_circuit_runs"]
    assert record["qaoa_call_count"] == 14
    expected_bitstring = "".join(str(reference_bits[index]) for index in sorted(reference_bits))
    assert record["result"]["bitstring"] == expected_bitstring
    assert len(output["qaoa_history"]) == 14
    assert len(output["qaoa_history"][0]["correlation_matrix"]) == 32
    assert output["assignments"][0]["bitstring"] == record["result"]["bitstring"]
    assert {path.name for path in tmp_path.glob("*.json")} == expected_artifacts
    for artifact_name, output_key in (
        ("results.json", "results"),
        ("assignments.json", "assignments"),
        ("reduction_history.json", "reduction_history"),
        ("qaoa_history.json", "qaoa_history"),
        ("experiment_log.json", "experiment_log"),
    ):
        assert json.loads((tmp_path / artifact_name).read_text(encoding="utf-8")) == output[output_key]


def test_reduced_energy_is_evaluated_after_rqaoa_merge():
    matrix = np.asarray([[1.0, 2.0], [0.0, 3.0]])
    seed = np.asarray([1, 1])
    steps = [
        {
            "method": "rqaoa_quantum_correlation",
            "kept_variable": 0,
            "eliminated_variable": 1,
            "relation": "Zi = Zj",
        }
    ]

    energies = _measure_reduced_energies(matrix, seed, steps)

    assert energies == [6.0]


def test_reduced_energy_is_null_when_qiro_fix_conflicts_with_seed():
    matrix = np.asarray([[1.0, 2.0], [0.0, 3.0]])
    seed = np.asarray([1, 0])
    steps = [
        {
            "method": "qiro_quantum_spin_bias",
            "fixed_variable": 0,
            "eliminated_variable": 0,
            "fixed_value": 0,
            "relation": "Zi = +1",
        }
    ]

    energies = _measure_reduced_energies(matrix, seed, steps)

    assert energies == [None]


def test_reduced_energy_is_evaluated_after_qiro_fix():
    matrix = np.asarray([[1.0, 2.0], [0.0, 3.0]])
    seed = np.asarray([1, 0])
    steps = [
        {
            "method": "qiro_quantum_spin_bias",
            "fixed_variable": 0,
            "eliminated_variable": 0,
            "fixed_value": 1,
            "relation": "Zi = -1",
        }
    ]

    energies = _measure_reduced_energies(matrix, seed, steps)

    assert energies == [1.0]
