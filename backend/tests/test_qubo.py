import numpy as np
import pandas as pd
import pytest

from outer_layer.distance_matrix import build_distance_matrix
from outer_layer.qubo.decode_solution import decode_solution
from outer_layer.qubo.qubo_builder import build_position_qubo


def build_four_customer_qubo():
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
            "cost_per_km": [1.0, 1.2],
        }
    )
    points = customers[["customer_id", "lat", "lon"]].rename(
        columns={"customer_id": "id"}
    )
    return build_position_qubo(customers, warehouses, build_distance_matrix(points))


def test_four_customer_two_warehouse_qubo_has_32_variables_and_decodes():
    qubo = build_four_customer_qubo()
    assert qubo.variable_count == 32

    bits = np.zeros(qubo.variable_count, dtype=int)
    for position, customer in enumerate(qubo.variables.customers):
        bits[qubo.variables.index("w1", customer, position)] = 1

    decoded = decode_solution(bits, qubo)
    assert decoded["warehouse_id"] == "w1"
    assert decoded["route"] == ["c1", "c2", "c3", "c4"]
    assert decoded["feasible"] is True
    assert np.isfinite(qubo.energy(bits))
    assert qubo.energy(bits) < qubo.energy(np.zeros(qubo.variable_count, dtype=int))


def test_decoder_rejects_missing_customer():
    qubo = build_four_customer_qubo()
    bits = np.zeros(qubo.variable_count, dtype=int)
    bits[qubo.variables.index("w1", "c1", 0)] = 1

    with pytest.raises(ValueError, match="one-customer-per-position"):
        decode_solution(bits, qubo)


def test_qubo_energy_requires_a_binary_vector_of_matching_length():
    qubo = build_four_customer_qubo()
    with pytest.raises(ValueError, match="bitstring"):
        qubo.energy([0, 1])
