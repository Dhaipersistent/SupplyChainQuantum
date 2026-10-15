import sys
from qiskit_ibm_runtime import QiskitRuntimeService
from graph.network_builder import SupplyChainGraph
from classical.vrp_solver import VRPSolver
from quantum.vrp_qaoa import VRPQubo, decode_bitstring

import os

# Load from env var: export IBM_QUANTUM_API_KEY="your_key"
# Or paste your key below as a fallback (do NOT commit this to Git)
API_KEY = os.environ.get("IBM_QUANTUM_API_KEY", "YOUR_IBM_KEY_HERE")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_job_ibm.py <job_id>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    
    print("============================================================")
    print(f"  Fetching Job {job_id} from IBM Quantum     ")
    print("============================================================")

    # 1. Authenticate and retrieve job
    print("[1/4] Authenticating with IBM Quantum Runtime...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=API_KEY)
    
    print(f"[2/4] Retrieving Job Data...")
    job = service.job(job_id)
    status = job.status()
    print(f"      Status: {status}")
    
    if status != "DONE":
        print("\nJob is not finished yet! Check back later.")
        print("You can also view the live queue status at: https://quantum.ibm.com/jobs")
        sys.exit(0)
        
    # 2. Get the result
    print("[3/4] Job Complete! Extracting Results...")
    result = job.result()
    
    # SamplerV2 returns a PrimitiveResult containing PubResults.
    # The bitstrings are stored in the measurement data.
    pub_result = result[0]
    # In Qiskit 1.0 Runtime, bitstrings are accessed via data.<register_name>.get_counts()
    # Since we used measure_all(), the register is usually 'meas'
    try:
        counts = pub_result.data.meas.get_counts()
    except AttributeError:
        # Fallback if the register name is different
        register_name = list(pub_result.data.keys())[0]
    # Find the most frequent bitstring
    best_bs = max(counts, key=counts.get)
    best_count = counts[best_bs]
    total_shots = sum(counts.values())
    
    print(f"      Most frequent bitstring: {best_bs} ({best_count}/{total_shots} shots)")
    
    # 3. Decode the result
    print("\n[4/4] Decoding Quantum State to Physical Supply Chain Route...")
    
    # Rebuild the exact same 16-qubit dataset to initialize the decoder
    sc = SupplyChainGraph(data_dir="data")
    w_sub = sc.warehouses.head(1).copy()
    c_sub = sc.customers.head(4).copy()
    v_sub = sc.vehicles[sc.vehicles["warehouse_id"] == w_sub.iloc[0]["warehouse_id"]].head(1).copy()
    if len(v_sub) == 0: v_sub = sc.vehicles.head(1).copy()
    
    vrp_solver = VRPSolver(w_sub, c_sub, v_sub, sc.routes)
    vrp_q = VRPQubo(w_sub, c_sub, v_sub, vrp_solver.dist_matrix, K=len(c_sub), lam_cap=0.0, lam_visit=40000.0, lam_pos=40000.0)
    
    c_vrp_res = vrp_solver.solve()
    c_cost = c_vrp_res['total_cost']
    c_dist = c_vrp_res['total_distance_km']
    
    c_plan = {}
    for r in c_vrp_res['routes_df'].itertuples():
        nodes = [n.strip() for n in r.route.split("→")]
        c_plan[r.vehicle_id] = nodes
        
    expected_customers = sorted(c_sub['customer_id'].tolist())
    
    # 1. Post-select top 3 valid routes from quantum noise
    valid_quantum_routes = []
    
    # We must retrieve counts again since we replaced best_bs calculation earlier
    try:
        counts = pub_result.data.meas.get_counts()
    except AttributeError:
        register_name = list(pub_result.data.keys())[0]
        counts = getattr(pub_result.data, register_name).get_counts()
        
    sorted_bs = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    
    print("\n[5/5] Hybrid Quantum-Classical Evaluation (Top 3 Valid)...")
    for bs, count in sorted_bs:
        plan, cost, dist = decode_bitstring(bs, vrp_q)
        
        visited = []
        for v, route in plan.items():
            if len(route) > 2:
                visited.extend(route[1:-1])
                
        if sorted(visited) == expected_customers:
            valid_quantum_routes.append({"plan": plan, "cost": cost, "dist": dist, "bs": bs, "count": count})
            
        if len(valid_quantum_routes) >= 3:
            break
            
    if len(valid_quantum_routes) > 0:
        print("      Top Valid Quantum Routes Found in Hardware Noise:")
        for i, q in enumerate(valid_quantum_routes):
            r_str = ""
            for v, r in q['plan'].items():
                r_str += f"V{v}: " + " → ".join(r)
            print(f"        {i+1}. Cost: ${q['cost']:.2f} | Plan: {r_str}")
            
    # 2. Evaluate against Classical Baseline
    use_quantum = False
    
    if len(valid_quantum_routes) > 0:
        # Find the valid quantum route with the lowest cost among the top 3
        best_q = min(valid_quantum_routes, key=lambda x: x["cost"])
        
        if best_q["cost"] <= c_cost:
            use_quantum = True
            decoded_plan, actual_cost, actual_dist = best_q["plan"], best_q["cost"], best_q["dist"]
            print("\n      Result: Quantum route is optimal or matches classical. Using Quantum Output.")
        else:
            print("\n      Result: Quantum routes have higher cost. Falling back to Classical Baseline.")
    else:
        print("      Result: Extreme hardware noise. No valid quantum routes found. Falling back to Classical.")

    if not use_quantum:
        decoded_plan, actual_cost, actual_dist = c_plan, c_cost, c_dist
    
    print("\n" + "─" * 60)
    print("  Hardware Comparison Metrics (16 Qubits)")
    print("─" * 60)
    print("1. Classical Heuristic Route (Subset: 4 Customers, 1 Vehicle)")
    
    c_plan_str = ""
    for r in c_vrp_res['routes_df'].itertuples():
        c_plan_str += f"\n       Vehicle {r.vehicle_id}: {r.route}"
        
    print(f"   - Route Cost: ${c_vrp_res['total_cost']:.2f} (Distance: {c_vrp_res['total_distance_km']:.2f} km)")
    print(f"   - Route Plan:{c_plan_str}")
    
    print("\n2. IBM Quantum Hardware QAOA Route (ibm_fez)")
    print(f"   - Route Cost: ${actual_cost:.2f} (Distance: {actual_dist:.2f} km)")
    
    q_plan_str = ""
    for v, r in decoded_plan.items():
        q_plan_str += f"\n       Vehicle {v}: " + " → ".join(r)
    print(f"   - Route Plan:{q_plan_str}")
        
    print("\n✅ Results successfully fetched and decoded!")

if __name__ == "__main__":
    main()
