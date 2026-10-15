from collections.abc import Iterable

import numpy as np


def add_exactly_one_penalty(
    matrix: np.ndarray,
    indices: Iterable[int],
    penalty: float,
) -> None:
    """Add penalty * (sum(x) - 1)^2 to an upper-triangular QUBO matrix."""
    variables = list(indices)
    if not variables or penalty <= 0:
        raise ValueError("An exactly-one constraint needs variables and a positive penalty")
    for index in variables:
        matrix[index, index] -= penalty
    for offset, left in enumerate(variables):
        for right in variables[offset + 1 :]:
            i, j = sorted((left, right))
            matrix[i, j] += 2 * penalty
