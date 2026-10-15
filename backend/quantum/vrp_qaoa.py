import numpy as np
import pandas as pd
from qiskit.circuit import QuantumCircuit, ParameterVector
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator
from scipy.optimize import minimize
from qiskit import transpile

class VRPQubo:
    def __init__(self, warehouses, customers, vehicles, dist_matrix, K=None, lam_cap=100.0, lam_visit=100.0, lam_pos=100.0):
        self.W = warehouses
        self.C = customers
        self.V = vehicles
        self.D = dist_matrix
        self.I = list(customers["customer_id"])
        self.Vs = list(vehicles["vehicle_id"])
        self.K = K or len(self.I)
        self.n = len(self.I) * self.K * len(self.Vs)
        self.lam = (lam_cap, lam_visit, lam_pos)
        self.Q = np.zeros((self.n, self.n))
        self._build()

    def idx(self, i, k, v):
        I, K, V = self.I, self.K, self.Vs
        return I.index(i) * K * len(V) + k * len(V) + V.index(v)

    def _build(self):
        self._add_objective()
        self._add_capacity()
        self._add_visit()
        self._add_position()

    def _add_objective(self):
        for vrow in self.V.itertuples():
            v, cv, wh = vrow.vehicle_id, vrow.cost_per_km, vrow.warehouse_id
            for k in range(self.K - 1):
                for ci in self.I:
                    for cj in self.I:
                        if ci == cj: continue
                        w = cv * self.D.get((ci, cj), 0)
                        a = self.idx(ci, k, v)
                        b = self.idx(cj, k+1, v)
                        self.Q[min(a, b), max(a, b)] += w
            # depot legs
            for ci in self.I:
                d1 = cv * self.D.get((wh, ci), 0)
                d2 = cv * self.D.get((ci, wh), 0)
                a1 = self.idx(ci, 0, v)
                a2 = self.idx(ci, self.K - 1, v)
                self.Q[a1, a1] += d1
                self.Q[a2, a2] += d2

    def _add_capacity(self):
        lam = self.lam[0]
        for vrow in self.V.itertuples():
            v, Qv = vrow.vehicle_id, vrow.capacity_kg
            for ci in self.I:
                qi = float(self.C.loc[self.C.customer_id == ci, "demand_units"].values[0])
                for k in range(self.K):
                    a = self.idx(ci, k, v)
                    self.Q[a, a] += lam * (qi**2 - 2*Qv*qi)
                for cj in self.I:
                    if cj <= ci: continue
                    qj = float(self.C.loc[self.C.customer_id == cj, "demand_units"].values[0])
                    for kk in range(self.K):
                        a = self.idx(ci, kk, v)
                        b = self.idx(cj, kk, v)
                        self.Q[min(a, b), max(a, b)] += lam * 2 * qi * qj

    def _add_visit(self):
        lam = self.lam[1]
        for ci in self.I:
            indices = [self.idx(ci, k, v) for v in self.Vs for k in range(self.K)]
            for a in indices:
                self.Q[a, a] -= lam
            for ii, a in enumerate(indices):
                for b in indices[ii+1:]:
                    self.Q[min(a, b), max(a, b)] += lam * 2

    def _add_position(self):
        lam = self.lam[2]
        for v in self.Vs:
            for k in range(self.K):
                indices = [self.idx(ci, k, v) for ci in self.I]
                for a in indices:
                    self.Q[a, a] -= lam
                for ii, a in enumerate(indices):
                    for b in indices[ii+1:]:
                        self.Q[min(a, b), max(a, b)] += lam * 2

    def to_ising(self):
        n = self.n
        h = np.zeros(n)
        J = {}
        offset = 0.0
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    h[i] += self.Q[i, i] / 2
                    offset += self.Q[i, i] / 2
                else:
                    J[(i, j)] = self.Q[i, j] / 4
                    h[i] += self.Q[i, j] / 4
                    h[j] += self.Q[i, j] / 4
                    offset += self.Q[i, j] / 4
        return h, J, offset

def ising_to_pauli(h, J, n):
    ops, coeffs = [], []
    for i, hi in enumerate(h):
        if abs(hi) > 1e-10:
            pauli_str = "I"*i + "Z" + "I"*(n-i-1)
            ops.append(pauli_str)
            coeffs.append(-float(hi))
    for (i, j), Jij in J.items():
        if abs(Jij) > 1e-10:
            pauli_list = ["I"]*n
            pauli_list[i] = "Z"
            pauli_list[j] = "Z"
            ops.append("".join(pauli_list))
            coeffs.append(-float(Jij))
    if not ops:
        ops.append("I"*n)
        coeffs.append(0.0)
    return SparsePauliOp(ops, coeffs=coeffs)

def build_qaoa_circuit(cost_op, p=1):
    n = cost_op.num_qubits
    gammas = ParameterVector("gamma", length=p)
    betas = ParameterVector("beta", length=p)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for layer in range(p):
        for pauli_term, coeff in zip(cost_op.paulis, cost_op.coeffs):
            qubits = [i for i, c in enumerate(str(pauli_term)) if c == 'Z']
            if len(qubits) == 1:
                qc.rz(-2 * float(coeff.real) * gammas[layer], qubits[0])
            elif len(qubits) == 2:
                i, j = qubits
                qc.cx(i, j)
                qc.rz(-2 * float(coeff.real) * gammas[layer], j)
                qc.cx(i, j)
        for q in range(n):
            qc.rx(2 * betas[layer], q)
    qc.measure_all()
    return qc, gammas, betas

def bitstring_to_cost(bitstring, qubo):
    x = np.array([int(b) for b in reversed(bitstring)])
    return float(x @ qubo.Q @ x)

def evaluate_sampler_results(counts, qubo):
    best_bs, best_cost = None, np.inf
    weighted_cost = 0.0
    total = sum(counts.values())
    for bs, cnt in counts.items():
        c = bitstring_to_cost(bs, qubo)
        weighted_cost += c * cnt / total
        if c < best_cost:
            best_cost, best_bs = c, bs
    return best_bs, best_cost, weighted_cost

def decode_bitstring(bitstring, qubo):
    x = np.array([int(b) for b in reversed(bitstring)])
    raw_routes = {v: [None] * qubo.K for v in qubo.Vs}
    
    for ci in qubo.I:
        for k in range(qubo.K):
            for v in qubo.Vs:
                if x[qubo.idx(ci, k, v)] == 1:
                    raw_routes[v][k] = ci
                    
    decoded_plan = {}
    actual_cost = 0.0
    actual_dist = 0.0
    
    for vrow in qubo.V.itertuples():
        v, cv, wh = vrow.vehicle_id, vrow.cost_per_km, vrow.warehouse_id
        route = [c for c in raw_routes[v] if c is not None]
        
        if not route:
            continue
            
        decoded_plan[v] = [wh] + route + [wh]
        dist = 0.0
        dist += qubo.D.get((wh, route[0]), 0)
        for i in range(len(route) - 1):
            dist += qubo.D.get((route[i], route[i+1]), 0)
        dist += qubo.D.get((route[-1], wh), 0)
        
        actual_dist += dist
        actual_cost += dist * cv
        
    return decoded_plan, actual_cost, actual_dist

def run_qaoa_vrp(warehouses, customers, vehicles, dist_matrix, p_layers=1, shots=1024, seed=42):
    print("=" * 60)
    print("  VRP QUBO QAOA Benchmark")
    print("=" * 60)
    vrp_q = VRPQubo(warehouses, customers, vehicles, dist_matrix, K=len(customers), lam_cap=0.0, lam_visit=40000.0, lam_pos=40000.0)
    print(f"[QUBO] Variables (qubits) = {vrp_q.n}")
    print(f"       Q matrix shape     = {vrp_q.Q.shape}")

    h, J, offset = vrp_q.to_ising()
    n_nonzero_J = sum(1 for v in J.values() if abs(v) > 1e-10)
    print(f"[Ising] Non-zero local fields = {np.sum(np.abs(h) > 1e-10)}")
    print(f"        Non-zero couplings J  = {n_nonzero_J}")

    cost_op = ising_to_pauli(h, J, vrp_q.n)
    print(f"[Pauli] Terms in H_C          = {len(cost_op)}")

    qc, gammas, betas = build_qaoa_circuit(cost_op, p=p_layers)
    print(f"\n[QAOA] Depth p = {p_layers}")
    print(f"       Qubits = {qc.num_qubits}")
    print(f"       Gates  = {qc.size()}")

    # Classical Optimization Loop
    def cost_func(params):
        param_dict = {}
        for i, g in enumerate(gammas):
            param_dict[g] = params[i]
        for i, b in enumerate(betas):
            param_dict[b] = params[p_layers + i]
        bound = qc.assign_parameters(param_dict)
        bound_no_meas = bound.remove_final_measurements(inplace=False)
        from qiskit.quantum_info import Statevector
        sv = Statevector(bound_no_meas)
        return sv.expectation_value(cost_op).real

    x0 = np.random.default_rng(seed).uniform(0, 2 * np.pi, 2 * p_layers)
    print("\n[QAOA] Starting optimization (COBYLA)...")
    result = minimize(cost_func, x0, method="COBYLA", options={"maxiter": 50, "rhobeg": 0.5})
    
    print(f"\n[Optimiser] Converged = {result.success}")
    print(f"            Optimal g = {result.x[:p_layers].round(4)}")
    print(f"            Optimal b = {result.x[p_layers:].round(4)}")
    print(f"            E[H_C]    = {result.fun:.4f}")

    # Sample final bitstrings
    param_dict = {}
    for i, g in enumerate(gammas):
        param_dict[g] = result.x[i]
    for i, b in enumerate(betas):
        param_dict[b] = result.x[p_layers + i]
    
    bound = qc.assign_parameters(param_dict)
    backend = AerSimulator(method="statevector", seed_simulator=seed)
    tc = transpile(bound, backend)
    job = backend.run(tc, shots=shots)
    counts = job.result().get_counts()

    best_bs, best_cost, avg_cost = evaluate_sampler_results(counts, vrp_q)
    print(f"\n[Sampling ({shots} shots)]")
    print(f" Best bitstring cost : {best_cost:.4f}")
    print(f" Avg weighted cost   : {avg_cost:.4f}")
    print(f" Best bitstring      : {best_bs}")

    # Approximation Ratio
    min_cost = np.inf
    # Only brute force if qubits <= 12 to avoid long waits
    if vrp_q.n <= 12:
        for bits in range(2**vrp_q.n):
            x = np.array([int(b) for b in format(bits, f"0{vrp_q.n}b")])
            c = float(x @ vrp_q.Q @ x)
            if c < min_cost:
                min_cost = c
        approx_ratio = best_cost / min_cost if min_cost > 0 else np.nan
        print(f"\n[Benchmark]")
        print(f" Brute-force optimum : {min_cost:.4f}")
        print(f" QAOA best           : {best_cost:.4f}")
        print(f" Approximation ratio : {approx_ratio:.4f} (1.0 = optimal)")
    else:
        min_cost = np.nan
        approx_ratio = np.nan
        print(f"\n[Benchmark] Skipping brute-force optimum for {vrp_q.n} qubits (too large).")

    decoded_plan, actual_cost, actual_dist = decode_bitstring(best_bs, vrp_q)

    return {
        "best_cost": best_cost,
        "best_bitstring": best_bs,
        "decoded_plan": decoded_plan,
        "actual_cost": actual_cost,
        "actual_dist": actual_dist,
        "min_cost": min_cost,
        "approx_ratio": approx_ratio
    }
