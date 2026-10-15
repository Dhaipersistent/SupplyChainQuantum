"""
main.py — CLI entry-point to run the full pipeline without the dashboard.

Usage:
    python main.py [--generate-data] [--qiskit]

Steps:
    1. (optional) Generate synthetic data
    2. Build supply-chain graph
    3. Run Unified Classical Optimizer (MILP)
    4. Run quantum / SA supplier selection
    5. Print comparison metrics
"""

import argparse
import pandas as pd

from data.generate_data          import main as generate_data
from graph.network_builder       import SupplyChainGraph
from classical.unified_optimizer import UnifiedClassicalOptimizer
from quantum.vrp_qaoa             import run_qaoa_vrp
from classical.vrp_solver         import VRPSolver

def run(use_qiskit: bool = False):
    print("\n" + "═" * 60)
    print("  End-to-End Supply Chain Optimization")
    print("═" * 60)

    # ── 1. Graph ────────────────────────────────────────────────────────
    print("\n[1/4] Building supply chain graph …")
    sc = SupplyChainGraph(data_dir="data")
    s  = sc.summary()
    print(f"      Nodes  : {s['total_nodes']}  |  Edges : {s['total_edges']}")
    print(f"      Demand : {s['total_demand']} units")

    # ── 2. Classical Unified MILP ───────────────────────────────────────
    print("\n[2/4] Unified Classical Optimizer (Supplier + Inv + Routing) …")
    unified = UnifiedClassicalOptimizer(sc.suppliers, sc.warehouses, sc.customers, sc.routes, sc.vehicles)
    u_res = unified.optimize()
    print(f"      Status   : {u_res['status']}")
    print(f"      Selected : {u_res['selected_suppliers']}")
    # ── 3. VRP Benchmark: Classical vs Quantum (Subset) ──────────────────
    print("\n[3/3] VRP Benchmark: Classical Heuristic vs Quantum QAOA (Subset) …")
    # Take a small subset to make it feasible for a quantum simulator
    w_sub = sc.warehouses.head(1).copy()
    c_sub = sc.customers.head(2).copy()
    v_sub = sc.vehicles[sc.vehicles["warehouse_id"] == w_sub.iloc[0]["warehouse_id"]].head(1).copy()
    if len(v_sub) == 0: v_sub = sc.vehicles.head(1).copy()
    
    # A. Run Classical VRP Heuristic on the subset
    vrp_solver_sub = VRPSolver(w_sub, c_sub, v_sub, sc.routes)
    c_vrp_res = vrp_solver_sub.solve()
    
    # B. Run Quantum VRP QAOA on the exact same subset
    vrp_res = run_qaoa_vrp(w_sub, c_sub, v_sub, vrp_solver_sub.dist_matrix, p_layers=1, shots=1024)

    # ── Comparison ───────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  Comparison Metrics")
    print("─" * 60)
    print("1. Unified Supply Chain (Classical MILP on FULL dataset)")
    print(f"   - Selected Suppliers: {u_res['selected_suppliers']}")
    print(f"   - Total Cost: ${u_res['total_cost']:,.2f}")
    
    print("\n2. Vehicle Routing Problem (Subset: 1 Warehouse, 2 Customers, 1 Vehicle)")
    
    c_plan_str = ""
    for r in c_vrp_res['routes_df'].itertuples():
        c_plan_str += f"\n       Vehicle {r.vehicle_id}: {r.route}"
        
    print(f"   [Classical Heuristic]")
    print(f"   - Route Cost: ${c_vrp_res['total_cost']:.2f} (Distance: {c_vrp_res['total_distance_km']:.2f} km)")
    print(f"   - Route Plan:{c_plan_str}")
    
    if vrp_res:
        q_plan_str = ""
        for v, r in vrp_res['decoded_plan'].items():
            q_plan_str += f"\n       Vehicle {v}: " + " → ".join(r)
            
        print(f"\n   [Quantum QAOA]")
        print(f"   - Route Cost: ${vrp_res['actual_cost']:.2f} (Distance: {vrp_res['actual_dist']:.2f} km)")
        print(f"   - Route Plan:{q_plan_str}")
        print(f"   - QUBO Energy: {vrp_res['best_cost']:.2f} (Optimizer objective value)")

    print("\n✅  Pipeline complete.\n")

    return u_res, vrp_res


def run_research_pipeline(
    *,
    reduction_method: str = "rqaoa",
    target_variables: int = 20,
    shots: int = 2048,
):
    """Run the Aer-based quantum reduction and reconstructed assignment workflow."""
    from pathlib import Path

    from outer_layer.improvement_loop import run_improvement_loop

    sc = SupplyChainGraph(data_dir="data")
    result = run_improvement_loop(
        sc.customers,
        sc.warehouses,
        sc.vehicles,
        n_clusters=4,
        reduction_method=reduction_method,
        target_variables=target_variables,
        shots=shots,
        output_dir=Path(__file__).resolve().parent / "output",
    )
    for cluster in result["results"]:
        assignment = cluster["result"]
        print(
            f"Cluster {cluster['cluster_id']}: "
            f"{cluster['variable_count']} -> {cluster['reduced_variable_count']} variables, "
            f"{assignment['warehouse_id']} / {' -> '.join(assignment['route'])}, "
            f"energy={assignment['energy']:.6f}"
        )
    print("Artifacts written to backend/output/")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-data", action="store_true",
                        help="Regenerate synthetic data before running")
    parser.add_argument("--qiskit", action="store_true",
                        help="Use Qiskit QAOA instead of Simulated Annealing")
    parser.add_argument(
        "--research-pipeline",
        action="store_true",
        help="Run Aer-shot RQAOA or QIRO reduction followed by Warm Start QAOA",
    )
    parser.add_argument(
        "--reduction-method",
        choices=("rqaoa", "qiro"),
        default="rqaoa",
        help="Quantum-assisted reduction algorithm for --research-pipeline",
    )
    parser.add_argument(
        "--target-variables",
        type=int,
        default=20,
        help="Maximum active variables before Warm Start QAOA",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=2048,
        help="Aer measurement shots per QAOA expectation estimate",
    )
    args = parser.parse_args()

    if args.generate_data:
        print("[0/4] Generating synthetic data …")
        generate_data()

    if args.research_pipeline:
        run_research_pipeline(
            reduction_method=args.reduction_method,
            target_variables=args.target_variables,
            shots=args.shots,
        )
    else:
        run(use_qiskit=args.qiskit)
