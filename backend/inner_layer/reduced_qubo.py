from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ReducedQubo:
    """Upper-triangular QUBO plus an affine map back to its original variables."""

    matrix: np.ndarray
    variable_ids: tuple[int, ...]
    original_count: int
    expressions: list[tuple[int | None, float, float]]
    offset: float = 0.0
    history: list[dict[str, object]] = field(default_factory=list)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> "ReducedQubo":
        upper = np.triu(np.asarray(matrix, dtype=float))
        if upper.ndim != 2 or upper.shape[0] != upper.shape[1]:
            raise ValueError("QUBO matrix must be square")
        if not np.isfinite(upper).all():
            raise ValueError("QUBO coefficients must be finite")
        count = upper.shape[0]
        return cls(
            matrix=upper.copy(),
            variable_ids=tuple(range(count)),
            original_count=count,
            expressions=[(index, 1.0, 0.0) for index in range(count)],
        )

    @property
    def variable_count(self) -> int:
        return len(self.variable_ids)

    @property
    def reconstruction_map(self) -> list[dict[str, int | float | None]]:
        return [
            {
                "original_variable": original_index,
                "active_variable": (
                    None if active_index is None else self.variable_ids[active_index]
                ),
                "factor": factor,
                "constant": constant,
            }
            for original_index, (active_index, factor, constant) in enumerate(self.expressions)
        ]

    def energy(self, bits: list[int] | np.ndarray) -> float:
        values = np.asarray(bits, dtype=float)
        if values.shape != (self.variable_count,) or not np.isin(values, [0, 1]).all():
            raise ValueError("bits must contain one binary value per active variable")
        return float(values @ self.matrix.diagonal() + sum(
            self.matrix[i, j] * values[i] * values[j]
            for i in range(self.variable_count)
            for j in range(i + 1, self.variable_count)
        ) + self.offset)

    def reconstruct(self, bits: list[int] | np.ndarray) -> np.ndarray:
        values = np.asarray(bits)
        if values.shape != (self.variable_count,) or not np.isin(values, [0, 1]).all():
            raise ValueError("bits must contain one binary value per active variable")
        values = values.astype(int)
        original = np.empty(self.original_count, dtype=int)
        for original_index, (active_index, factor, constant) in enumerate(self.expressions):
            value = constant if active_index is None else factor * values[active_index] + constant
            if value not in (0, 1):
                raise ValueError("Reduction map reconstructed a non-binary variable")
            original[original_index] = int(value)
        return original

    def project(self, original_bits: list[int] | np.ndarray) -> np.ndarray:
        original = np.asarray(original_bits)
        if original.shape != (self.original_count,) or not np.isin(original, [0, 1]).all():
            raise ValueError("original_bits must contain one binary value per original variable")
        original = original.astype(int)
        projected = np.empty(self.variable_count, dtype=int)
        assigned = np.zeros(self.variable_count, dtype=bool)
        for original_index, (active_index, factor, constant) in enumerate(self.expressions):
            if active_index is None:
                if original[original_index] != constant:
                    raise ValueError("Original bitstring conflicts with a fixed reduction")
                continue
            value = int((original[original_index] - constant) / factor)
            if value not in (0, 1) or not np.isclose(
                factor * value + constant, original[original_index]
            ):
                raise ValueError("Original bitstring conflicts with an eliminated-variable relation")
            if assigned[active_index] and projected[active_index] != value:
                raise ValueError("Original bitstring conflicts with a merged-variable relation")
            projected[active_index] = value
            assigned[active_index] = True
        if not assigned.all():
            raise ValueError("Reduction map contains an unconstrained active variable")
        return projected

    def fix_variable(self, active_index: int, value: int, *, method: str) -> None:
        if value not in (0, 1) or active_index < 0 or active_index >= self.variable_count:
            raise ValueError("Invalid variable or fixing value")
        self._substitute({active_index: (None, 0.0, float(value))}, method=method)

    def merge_variables(
        self,
        kept_index: int,
        removed_index: int,
        *,
        complement: bool,
        method: str,
    ) -> None:
        if kept_index == removed_index:
            raise ValueError("Cannot merge a variable with itself")
        if min(kept_index, removed_index) < 0 or max(
            kept_index, removed_index
        ) >= self.variable_count:
            raise ValueError("Variable index is outside the QUBO")
        self._substitute(
            {removed_index: (kept_index, -1.0 if complement else 1.0, 1.0 if complement else 0.0)},
            method=method,
        )

    def _substitute(
        self,
        replacements: dict[int, tuple[int | None, float, float]],
        *,
        method: str,
    ) -> None:
        old_count = self.variable_count
        removed = set(replacements)
        kept_old = [index for index in range(old_count) if index not in removed]
        old_to_new = {old: new for new, old in enumerate(kept_old)}
        new_count = len(kept_old)
        old_expr_by_index: list[tuple[int | None, float, float] | None] = [
            None
        ] * old_count
        for index in kept_old:
            old_expr_by_index[index] = (old_to_new[index], 1.0, 0.0)
        for old_index, (target, factor, constant) in replacements.items():
            if target is None:
                old_expr_by_index[old_index] = (None, 0.0, constant)
            else:
                if target not in old_to_new:
                    raise ValueError("A merged variable must target a variable that remains active")
                old_expr_by_index[old_index] = (old_to_new[target], factor, constant)
        if any(expression is None for expression in old_expr_by_index):
            raise RuntimeError("Reduction map did not cover every prior variable")
        new_matrix = np.zeros((new_count, new_count), dtype=float)
        new_offset = self.offset

        for left in range(old_count):
            left_expression = old_expr_by_index[left]
            assert left_expression is not None
            target_left, factor_left, constant_left = left_expression
            diagonal = self.matrix[left, left]
            new_offset += diagonal * constant_left**2
            if target_left is not None:
                new_matrix[target_left, target_left] += diagonal * (
                    factor_left**2 + 2 * factor_left * constant_left
                )
            for right in range(left + 1, old_count):
                coefficient = self.matrix[left, right]
                right_expression = old_expr_by_index[right]
                assert right_expression is not None
                target_right, factor_right, constant_right = right_expression
                new_offset += coefficient * constant_left * constant_right
                if target_left is not None:
                    new_matrix[target_left, target_left] += (
                        coefficient * factor_left * constant_right
                    )
                if target_right is not None:
                    new_matrix[target_right, target_right] += (
                        coefficient * factor_right * constant_left
                    )
                if target_left is not None and target_right is not None:
                    if target_left == target_right:
                        new_matrix[target_left, target_left] += (
                            coefficient * factor_left * factor_right
                        )
                    else:
                        i, j = sorted((target_left, target_right))
                        new_matrix[i, j] += coefficient * factor_left * factor_right

        composed: list[tuple[int | None, float, float]] = []
        for active_index, factor, constant in self.expressions:
            if active_index is None:
                composed.append((None, factor, constant))
                continue
            new_active, new_factor, new_constant = old_expr_by_index[active_index]
            composed.append(
                (
                    new_active,
                    factor * new_factor,
                    factor * new_constant + constant,
                )
            )
        removed_variables = [
            self.variable_ids[index] for index in sorted(removed)
        ]
        self.expressions = composed
        self.variable_ids = tuple(self.variable_ids[index] for index in kept_old)
        self.matrix = np.triu(new_matrix)
        self.offset = float(new_offset)
        self.history.append(
            {
                "method": method,
                "removed_variables": removed_variables,
                "remaining_variables": self.variable_count,
            }
        )
