from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from itertools import permutations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from inner_layer.qiro import fix_biased_variables
from inner_layer.rqaoa import reduce_correlated_variables
from inner_layer.warm_start_qaoa import run_warm_start_qaoa
from outer_layer.clustering.kmeans_cluster import cluster_customers
from outer_layer.distance_matrix import (
    build_distance_matrix,
    haversine_km,
    nearest_warehouses,
)
from outer_layer.qubo.decode_solution import decode_solution
from outer_layer.qubo.qubo_builder import PositionQubo, build_position_qubo
from outer_layer.qubo.position_variables import PositionVariables
from inner_layer.reduced_qubo import ReducedQubo
from evaluation.evaluator import evaluate_cluster_solution


def _seed_route(
    customers: pd.DataFrame,
    warehouse_candidates: pd.DataFrame,
) -> tuple[str, list[str]]:
    customer_ids = customers["customer_id"].astype(str).tolist()
    ranked_warehouses = warehouse_candidates.assign(
        _score=warehouse_candidates.apply(
            lambda warehouse: float(warehouse["cost_per_km"])
            * sum(
                np.hypot(
                    (float(warehouse["lat"]) - float(customer["lat"]))
                    * np.cos(np.deg2rad(float(warehouse["lat"]))),
                    float(warehouse["lon"]) - float(customer["lon"]),
                )
                for _, customer in customers.iterrows()
            ),
            axis=1,
        )
    ).sort_values(["_score", "warehouse_id"], kind="stable")
    return str(ranked_warehouses.iloc[0]["warehouse_id"]), customer_ids


def _make_seed(
    variables: PositionVariables,
    warehouse: str,
    ordered_customers: list[str],
) -> np.ndarray:
    bits = np.zeros(variables.count, dtype=int)
    for position, customer in enumerate(ordered_customers):
        bits[variables.index(warehouse, customer, position)] = 1
    return bits


def _find_feasible_reduced_seed(
    reduced: ReducedQubo,
    qubo: PositionQubo,
    preferred_seed: np.ndarray,
) -> np.ndarray | None:
    """Find an initial feasible warm-start only; never changes the reduction."""
    try:
        projected = reduced.project(preferred_seed)
        decode_solution(reduced.reconstruct(projected), qubo)
        return projected
    except ValueError:
        pass

    for warehouse in qubo.variables.warehouses:
        for route in permutations(qubo.variables.customers):
            original = np.zeros(qubo.variable_count, dtype=int)
            for position, customer in enumerate(route):
                original[qubo.variables.index(warehouse, customer, position)] = 1
            try:
                projected = reduced.project(original)
                decode_solution(reduced.reconstruct(projected), qubo)
                return projected
            except ValueError:
                continue
    return None


def _measure_reduced_energies(
    matrix: np.ndarray,
    original_seed: np.ndarray,
    steps: list[dict[str, Any]],
) -> list[float | None]:
    """Evaluate each reduced QUBO at the projected original seed, when compatible."""
    reduced = ReducedQubo.from_matrix(matrix)
    energies: list[float | None] = []
    for step in steps:
        if step.get("fixed_value") is not None:
            variable_id = int(step.get("fixed_variable", step["eliminated_variable"]))
            reduced.fix_variable(
                reduced.variable_ids.index(variable_id),
                int(step["fixed_value"]),
                method=str(step["method"]),
            )
        else:
            kept_variable = int(step["kept_variable"])
            eliminated_variable = int(step["eliminated_variable"])
            reduced.merge_variables(
                reduced.variable_ids.index(kept_variable),
                reduced.variable_ids.index(eliminated_variable),
                complement=step["relation"] == "Zi = -Zj",
                method=str(step["method"]),
            )
        try:
            projected_seed = reduced.project(original_seed)
        except ValueError:
            energies.append(None)
        else:
            # Reduced QUBO energy includes its substitution offset and is not the original seed score.
            energies.append(reduced.energy(projected_seed))
    return energies


def _add_route_metrics(
    decoded: dict[str, Any],
    customers: pd.DataFrame,
    candidate_warehouses: pd.DataFrame,
) -> None:
    warehouse = candidate_warehouses.loc[
        candidate_warehouses["warehouse_id"].astype(str) == decoded["warehouse_id"]
    ].iloc[0]
    customer_rows = customers.set_index(customers["customer_id"].astype(str))
    ordered = [customer_rows.loc[customer] for customer in decoded["route"]]
    points = [
        (float(warehouse["lat"]), float(warehouse["lon"])),
        *[(float(row["lat"]), float(row["lon"])) for row in ordered],
        (float(warehouse["lat"]), float(warehouse["lon"])),
    ]
    distance = sum(
        haversine_km(*points[index], *points[index + 1])
        for index in range(len(points) - 1)
    )
    decoded["route_distance_km"] = distance
    decoded["travel_cost"] = distance * float(warehouse["cost_per_km"])


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_outputs(
    output_dir: Path,
    results: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    reduction_history: list[dict[str, Any]],
    qaoa_history: list[dict[str, Any]],
    experiment_log: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "results.json": results,
        "assignments.json": assignments,
        "reduction_history.json": reduction_history,
        "qaoa_history.json": qaoa_history,
        "experiment_log.json": experiment_log,
    }
    for name, payload in payloads.items():
        path = output_dir / name
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)


def run_improvement_loop(
    customers: pd.DataFrame,
    warehouses: pd.DataFrame,
    vehicles: pd.DataFrame,
    *,
    n_clusters: int = 4,
    target_variables: int = 20,
    qaoa_rounds: int = 2,
    warm_start_maxiter: int = 6,
    reduction_method: str = "rqaoa",
    shots: int = 2048,
    qiro_expectation_threshold: float = 0.05,
    output_dir: str | Path | None = None,
    run_hardware: bool = False,
) -> dict[str, Any]:
    """Run shot-based QAOA reduction before warm-start QAOA on each cluster."""
    if not 1 <= n_clusters <= len(customers):
        raise ValueError("n_clusters must be between 1 and the customer count")
    if not 1 <= target_variables <= 20:
        raise ValueError("target_variables must be between 1 and the 20-qubit hardware cap")
    if not 1 <= qaoa_rounds <= 5:
        raise ValueError("qaoa_rounds must be between 1 and 5")
    if not 1 <= warm_start_maxiter <= 30:
        raise ValueError("warm_start_maxiter must be between 1 and 30")
    if reduction_method not in {"rqaoa", "qiro"}:
        raise ValueError("reduction_method must be 'rqaoa' or 'qiro'")
    if shots < 1:
        raise ValueError("shots must be positive")
    if not 0.0 < qiro_expectation_threshold <= 1.0:
        raise ValueError("qiro_expectation_threshold must be in (0, 1]")
    if run_hardware:
        raise RuntimeError("IBM hardware is disabled; this research pipeline runs on Aer only")
    if "warehouse_id" not in vehicles.columns or "cost_per_km" not in vehicles.columns:
        raise ValueError("Vehicle data must include warehouse_id and cost_per_km")
    cluster_result = cluster_customers(customers, n_clusters=n_clusters)
    results: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    reduction_history: list[dict[str, Any]] = []
    qaoa_history: list[dict[str, Any]] = []
    experiment_log: list[dict[str, Any]] = []

    for cluster_id, members in cluster_result.customers.groupby("cluster_id", sort=True):
        centroid = cluster_result.centroids.loc[
            cluster_result.centroids["cluster_id"] == cluster_id
        ].iloc[0]
        warehouse_ids = nearest_warehouses(centroid, warehouses, count=min(2, len(warehouses)))
        if len(warehouse_ids) != 2:
            raise ValueError("At least two warehouses are required to build each cluster QUBO")
        candidate_warehouses = warehouses[
            warehouses["warehouse_id"].astype(str).isin(warehouse_ids)
        ].copy()
        rates = (
            vehicles[vehicles["warehouse_id"].astype(str).isin(warehouse_ids)]
            .groupby(vehicles["warehouse_id"].astype(str))["cost_per_km"]
            .min()
        )
        candidate_warehouses["cost_per_km"] = candidate_warehouses[
            "warehouse_id"
        ].astype(str).map(rates)
        if candidate_warehouses["cost_per_km"].isna().any():
            missing = candidate_warehouses.loc[
                candidate_warehouses["cost_per_km"].isna(), "warehouse_id"
            ].tolist()
            raise ValueError(f"No vehicle cost_per_km exists for candidate warehouses: {missing}")
        matrix_points = members[["customer_id", "lat", "lon"]].rename(
            columns={"customer_id": "id"}
        )
        distances = build_distance_matrix(matrix_points)
        qubo = build_position_qubo(members, candidate_warehouses, distances)
        original_variables = qubo.variables.count
        if original_variables != 2 * len(members) ** 2:
            raise RuntimeError("Position QUBO variable count does not match 2 * customers^2")

        seed_warehouse, seed_order = _seed_route(members, candidate_warehouses)
        seed = _make_seed(qubo.variables, seed_warehouse, seed_order)
        reduced = ReducedQubo.from_matrix(qubo.matrix)
        # Original seed energy means qubo.energy(seed) on the full, unreduced QUBO.
        cluster_qaoa_history: list[dict[str, Any]] = []

        def log_reductions(steps: list[dict[str, Any]]) -> None:
            reduced_energies = _measure_reduced_energies(qubo.matrix, seed, steps)
            for step in steps:
                reduction_call_count = int(step["iteration"])
                reduction_qaoa_calls = cluster_qaoa_history[:reduction_call_count]
                variables_before = int(step["previous_qubo_size"])
                variables_after = int(step["remaining_variables"])
                row = {
                    "cluster_id": int(cluster_id),
                    "solver_name": step["method"],
                    "algorithm": reduction_method,
                    "iteration": int(step["iteration"]),
                    "variables_before": variables_before,
                    "variables_after": variables_after,
                    "variable_count": variables_before,
                    "remaining_variables": variables_after,
                    "reduced_variable_count": int(step["reduced_qubo_size"]),
                    "reduced_qubo_energy": reduced_energies[int(step["iteration"]) - 1],
                    "correlation_value": step.get("correlation_value"),
                    "expectation_value": step.get("expectation_value"),
                    "eliminated_variable": step.get("eliminated_variable"),
                    "removed_variable": step.get("eliminated_variable"),
                    "kept_variable": step.get("kept_variable"),
                    "fixed_variables": step.get("fixed_variables", []),
                    "relation": step.get("relation"),
                    "shots": int(step["shots"]),
                    "qaoa_circuit_runs": int(step["circuit_runs"]),
                    "qaoa_call_count": reduction_call_count,
                    "aer_circuit_runs": sum(
                        int(call.get("circuit_runs", 0))
                        for call in reduction_qaoa_calls
                    ),
                    "optimizer_evaluations": int(step["optimizer_evaluations"]),
                    "optimizer_shots_per_evaluation": int(step["optimizer_shots"]),
                    "total_qaoa_shots": int(step["total_shots"]),
                    "simulator_backend": "aer_matrix_product_state",
                    "mps_max_bond_dimension": step.get("max_bond_dimension"),
                    "mps_truncation_threshold": step.get("truncation_threshold"),
                    "parameter_optimization": step.get("parameter_optimization"),
                    "timestamp": _timestamp(),
                }
                reduction_history.append(row)
                experiment_log.append(row.copy())

        if reduced.variable_count > target_variables:
            if reduction_method == "rqaoa":
                reduction_steps = reduce_correlated_variables(
                    reduced,
                    target_variables,
                    shots=shots,
                    qaoa_history=cluster_qaoa_history,
                )
            else:
                reduction_steps = fix_biased_variables(
                    reduced,
                    target_variables,
                    expectation_threshold=qiro_expectation_threshold,
                    shots=shots,
                    qaoa_history=cluster_qaoa_history,
                )
            log_reductions(reduction_steps)
        if reduced.variable_count > target_variables:
            raise RuntimeError(
                f"{reduction_method.upper()} left {reduced.variable_count} variables; "
                f"target is {target_variables}"
            )

        def is_feasible(active_bits: np.ndarray) -> bool:
            try:
                decode_solution(reduced.reconstruct(active_bits), qubo)
                return True
            except ValueError:
                return False

        reduced_seed = _find_feasible_reduced_seed(reduced, qubo, seed)
        if reduced_seed is None:
            raise RuntimeError(
                f"{reduction_method.upper()} reduction left no feasible original "
                "assignment in its affine reconstruction subspace"
            )
        best_bits = reduced_seed.copy()
        best_energy = reduced.energy(best_bits)
        solver_result = None
        qaoa_runtime = 0.0
        simulator_sample_feasible = False
        feedback_history: list[dict[str, Any]] = []
        for iteration in range(1, qaoa_rounds + 1):
            iteration_result = run_warm_start_qaoa(
                reduced.matrix,
                best_bits,
                maxiter=warm_start_maxiter,
                shots=shots,
                feasible_validator=is_feasible,
            )
            qaoa_runtime += iteration_result.runtime_seconds
            simulator_sample_feasible |= iteration_result.simulator_sample_feasible
            candidate_bits = np.asarray(iteration_result.bitstring, dtype=int)
            candidate_energy = reduced.energy(candidate_bits)
            candidate_feasible = is_feasible(candidate_bits)
            if candidate_feasible and candidate_energy < best_energy - 1e-9:
                best_bits = candidate_bits
                best_energy = candidate_energy
                feedback = "incumbent_improved"
            else:
                feedback = "retained_best_feasible_incumbent"
            cluster_qaoa_history.append(
                {
                    "algorithm": "warm_start_qaoa",
                    "cluster_id": int(cluster_id),
                    "iteration": iteration,
                    "variable_ids": list(reduced.variable_ids),
                    "shots": shots,
                    "expected_energy": iteration_result.energy,
                    "parameters": iteration_result.parameters,
                    "bitstring": candidate_bits.tolist(),
                    "feasible": candidate_feasible,
                    "backend": iteration_result.backend,
                }
            )
            feedback_entry = {
                "iteration": iteration,
                "feedback": feedback,
                "incumbent_energy": best_energy,
                "simulator_sample_feasible": iteration_result.simulator_sample_feasible,
            }
            feedback_history.append(feedback_entry)
            experiment_log.append(
                {
                    "cluster_id": int(cluster_id),
                    "solver_name": iteration_result.solver_name,
                    # Warm Start QAOA energy is its best feasible incumbent on the final reduced QUBO.
                    "energy": best_energy,
                    "runtime_seconds": iteration_result.runtime_seconds,
                    "variable_count": original_variables,
                    "reduced_variable_count": reduced.variable_count,
                    "hardware_backend": iteration_result.backend,
                    "timestamp": _timestamp(),
                    **feedback_entry,
                }
            )
            solver_result = iteration_result
        if solver_result is None:
            raise RuntimeError("Warm Start QAOA did not execute")
        qaoa_history.extend(
            {"cluster_id": int(cluster_id), **entry}
            for entry in cluster_qaoa_history
        )
        solver_result = replace(
            solver_result,
            bitstring=best_bits.tolist(),
            energy=best_energy - reduced.offset,
            runtime_seconds=qaoa_runtime,
            feasible=True,
            simulator_sample_feasible=simulator_sample_feasible,
        )
        reconstructed = reduced.reconstruct(best_bits)
        decoded = evaluate_cluster_solution(
            reconstructed,
            qubo,
            reduced.variable_count,
        )
        decoded["solver_sample_feasible"] = simulator_sample_feasible
        decoded["bitstring"] = "".join(str(bit) for bit in reconstructed.tolist())
        decoded["reduced_bitstring"] = "".join(str(bit) for bit in best_bits.tolist())
        _add_route_metrics(decoded, members, candidate_warehouses)
        solver_energy = solver_result.energy + reduced.offset
        record = {
            "cluster_id": int(cluster_id),
            "customer_ids": members["customer_id"].astype(str).tolist(),
            "candidate_warehouses": warehouse_ids,
            "warehouse_count": len(warehouse_ids),
            "position_count": len(qubo.variables.positions),
            "variable_count": original_variables,
            "reduced_variable_count": reduced.variable_count,
            "original_qubo_size": original_variables,
            "reduced_qubo_size": reduced.variable_count,
            "reduction_method": reduction_method,
            "reduced_qubo": reduced.matrix.tolist(),
            "reduced_qubo_offset": reduced.offset,
            "remaining_variable_ids": list(reduced.variable_ids),
            "elimination_history": [step.copy() for step in reduced.history],
            "reconstruction_map": reduced.reconstruction_map,
            "qaoa_call_count": len(cluster_qaoa_history),
            "aer_circuit_runs": sum(
                int(item.get("circuit_runs", 0)) for item in cluster_qaoa_history
            ),
            "variables_removed": original_variables - reduced.variable_count,
            "reduction_percentage": (
                (original_variables - reduced.variable_count) / original_variables * 100
            ),
            "hardware_eligible": (
                reduced.variable_count <= 20 and simulator_sample_feasible
            ),
            "simulator_sample_feasible": simulator_sample_feasible,
            "result": decoded,
            "feedback_history": feedback_history,
            "solver": {
                "name": solver_result.solver_name,
                "energy": solver_energy,
                "runtime_seconds": solver_result.runtime_seconds,
                "backend": solver_result.backend,
            },
        }
        results.append(record)
        assignments.append(
            {
                "cluster_id": int(cluster_id),
                "warehouse_id": decoded["warehouse_id"],
                "route": decoded["route"],
                "energy": decoded["energy"],
                "bitstring": decoded["bitstring"],
                "feasible": decoded["feasible"],
            }
        )

    output = {
        "clusters": cluster_result.customers.to_dict(orient="records"),
        "centroids": cluster_result.centroids.to_dict(orient="records"),
        "results": results,
        "assignments": assignments,
        "reduction_history": reduction_history,
        "qaoa_history": qaoa_history,
        "experiment_log": experiment_log,
    }
    if output_dir is not None:
        _write_outputs(
            Path(output_dir),
            results,
            assignments,
            reduction_history,
            qaoa_history,
            experiment_log,
        )
    return output
