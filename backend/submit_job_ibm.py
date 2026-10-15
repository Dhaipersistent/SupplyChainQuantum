import os
import pandas as pd
import numpy as np
from scipy.optimize import minimize

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit import transpile
from qiskit.quantum_info import Statevector

from graph.network_builder import SupplyChainGraph
from classical.vrp_solver import VRPSolver
from quantum.vrp_qaoa import VRPQubo, ising_to_pauli, build_qaoa_circuit

import os

# Load from env var: export IBM_QUANTUM_API_KEY="your_key"
# Or paste your key below as a fallback (do NOT commit this to Git)
API_KEY = os.environ.get("IBM_QUANTUM_API_KEY", "YOUR_IBM_KEY_HERE")

def main():
    print("============================================================")
    print("  Submitting 16-Qubit VRP QAOA to IBM Quantum Hardware      ")
    print("============================================================")

    # 1. Prepare the 16-qubit dataset (4 Customers, 1 Vehicle)
    print("\n[1/5] Preparing Supply Chain Data Subset (16 Qubits)...")
    sc = SupplyChainGraph(data_dir="data")
    w_sub = sc.warehouses.head(1).copy()
    c_sub = sc.customers.head(4).copy()
    v_sub = sc.vehicles[sc.vehicles["warehouse_id"] == w_sub.iloc[0]["warehouse_id"]].head(1).copy()
    if len(v_sub) == 0: 
        v_sub = sc.vehicles.head(1).copy()
    
    vrp_solver = VRPSolver(w_sub, c_sub, v_sub, sc.routes)
    
    # Build the QUBO and Circuit
    vrp_q = VRPQubo(w_sub, c_sub, v_sub, vrp_solver.dist_matrix, K=len(c_sub), lam_cap=0.0, lam_visit=40000.0, lam_pos=40000.0)
    print(f"      Variables (qubits) : {vrp_q.n}")
    
    h, J, offset = vrp_q.to_ising()
    cost_op = ising_to_pauli(h, J, vrp_q.n)
    
    p_layers = 1
    qc, gammas, betas = build_qaoa_circuit(cost_op, p=p_layers)
    
    # 2. Local Pre-Optimization
    # We find the optimal parameters locally so we don't wait in the IBM queue for 50 iterations!
    print("\n[2/5] Locally Pre-Optimizing QAOA Parameters (Statevector)...")
    def cost_func(params):
        param_dict = {gammas[i]: params[i] for i in range(p_layers)}
        param_dict.update({betas[i]: params[p_layers + i] for i in range(p_layers)})
        bound = qc.assign_parameters(param_dict)
        bound_no_meas = bound.remove_final_measurements(inplace=False)
        sv = Statevector(bound_no_meas)
        return sv.expectation_value(cost_op).real

    x0 = np.random.default_rng(42).uniform(0, 2 * np.pi, 2 * p_layers)
    result = minimize(cost_func, x0, method="COBYLA", options={"maxiter": 40, "rhobeg": 0.5})
    
    print(f"      Converged = {result.success}")
    print(f"      Optimal g = {result.x[:p_layers].round(4)}")
    print(f"      Optimal b = {result.x[p_layers:].round(4)}")
    
    # Bind the optimal parameters
    opt_dict = {gammas[i]: result.x[i] for i in range(p_layers)}
    opt_dict.update({betas[i]: result.x[p_layers + i] for i in range(p_layers)})
    bound_qc = qc.assign_parameters(opt_dict)
    
    # 3. Authenticate with IBM Quantum
    print("\n[3/5] Authenticating with IBM Quantum Runtime...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=API_KEY)
    
    # Find the least busy backend with at least 16 qubits
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=16)
    print(f"      Selected Backend: {backend.name} (Qubits: {backend.num_qubits})")

    # 4. Transpile for the specific hardware
    # We use optimization_level=3 for maximum gate fusion and error mitigation routing
    print(f"\n[4/5] Transpiling Circuit for {backend.name} (Optimization Level 3)...")
    transpiled_qc = transpile(bound_qc, backend, optimization_level=3)
    print(f"      Original Depth   : {bound_qc.depth()}")
    print(f"      Transpiled Depth : {transpiled_qc.depth()}")
    
    # 5. Submit the Job to IBM Hardware
    print("\n[5/5] Submitting Job to IBM Quantum (SamplerV2)...")
    # Resilience level 1 enables readout error mitigation
    sampler = SamplerV2(mode=backend)
    # Note: SamplerV2 doesn't have a top-level resilience_level option like EstimatorV2.
    
    job = sampler.run([transpiled_qc], shots=4096)
    print(f"\n✅ Job successfully submitted!")
    print(f"   Job ID: {job.job_id()}")
    print(f"   You can monitor the execution status live on your IBM Quantum Dashboard.")
    print(f"   Once complete, decode the most frequent bitstring to view the physical hardware route!")

if __name__ == "__main__":
    main()

