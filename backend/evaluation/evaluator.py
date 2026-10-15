from __future__ import annotations

import numpy as np

from evaluation.metrics import reduction_ratio
from outer_layer.qubo.decode_solution import decode_solution
from outer_layer.qubo.qubo_builder import PositionQubo


def evaluate_cluster_solution(
    original_bits: list[int] | np.ndarray,
    qubo: PositionQubo,
    reduced_variable_count: int,
) -> dict[str, object]:
    bits = np.asarray(original_bits, dtype=int)
    decoded = decode_solution(bits, qubo)
    return {
        **decoded,
        "bitstring": "".join(str(bit) for bit in bits.tolist()),
        "original_variables": qubo.variable_count,
        "reduced_variables": reduced_variable_count,
        "reduction_ratio": reduction_ratio(qubo.variable_count, reduced_variable_count),
    }
