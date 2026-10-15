"""
Classical supplier selection using weighted multi-criteria scoring.

Criteria (higher is better after normalisation):
    cost_per_unit      → lower is better
    reliability_score  → higher is better
    lead_time_days     → lower is better
    capacity           → higher is better

Greedy selection: rank by composite score, pick until demand is covered.
"""

import pandas as pd
import numpy as np


class ClassicalSupplierSelector:

    WEIGHTS = {
        "cost":        0.35,
        "reliability": 0.30,
        "lead_time":   0.20,
        "capacity":    0.15,
    }

    def __init__(self, suppliers_df: pd.DataFrame, total_demand: int):
        self.suppliers    = suppliers_df.copy()
        self.total_demand = total_demand
        self._score()

    # ------------------------------------------------------------------

    def _normalise(self, series: pd.Series, higher_is_better: bool) -> pd.Series:
        lo, hi = series.min(), series.max()
        norm = (series - lo) / (hi - lo + 1e-9)
        return norm if higher_is_better else 1 - norm

    def _score(self):
        df = self.suppliers
        df["_n_cost"]        = self._normalise(df["cost_per_unit"],     higher_is_better=False)
        df["_n_reliability"] = self._normalise(df["reliability_score"], higher_is_better=True)
        df["_n_lead_time"]   = self._normalise(df["lead_time_days"],    higher_is_better=False)
        df["_n_capacity"]    = self._normalise(df["capacity"],          higher_is_better=True)

        w = self.WEIGHTS
        df["score"] = (
            w["cost"]        * df["_n_cost"] +
            w["reliability"] * df["_n_reliability"] +
            w["lead_time"]   * df["_n_lead_time"] +
            w["capacity"]    * df["_n_capacity"]
        )
        self.suppliers = df.sort_values("score", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------

    def select(self) -> dict:
        """Greedily pick top-scored suppliers until demand is covered."""
        selected, covered, cost = [], 0, 0.0

        for r in self.suppliers.itertuples():
            if covered >= self.total_demand:
                break
            qty = min(r.capacity, self.total_demand - covered)
            selected.append(r.supplier_id)
            covered += qty
            cost    += qty * r.cost_per_unit

        cols = ["supplier_id", "name", "score",
                "cost_per_unit", "reliability_score", "lead_time_days", "capacity"]

        return {
            "selected_suppliers":   selected,
            "total_capacity":       covered,
            "total_cost":           round(cost, 2),
            "demand_met":           covered >= self.total_demand,
            "ranked_suppliers":     self.suppliers[cols].copy(),
        }
