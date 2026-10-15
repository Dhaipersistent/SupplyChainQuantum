#  Quantum-Ready Supply Chain Optimizer
## Semicolons · IBM Quantum Hackathon 2025

---

## Research prototype (current optimization path)

The research pipeline clusters customers with KMeans, builds one
two-candidate-warehouse position QUBO per cluster, then runs either RQAOA or
QIRO reduction using sampled p=1 QAOA expectation values on Qiskit Aer
(`matrix_product_state`, maximum bond dimension 64 and truncation threshold
`1e-10`). This bounded-MPS simulation is approximate; its settings and shot
counts are included in the QAOA history. Reduction uses fixed p=1 angles
(`gamma = beta = 0.5`) to initialize shot-based COBYLA optimization on the first
reduction round, then transfers those angles to subsequent recursive rounds.
The sampler can also optimize angles on every call. RQAOA uses the strongest measured `|<ZiZj>|` to
substitute a spin relation; QIRO fixes spins whose measured `|<Zi>|` clears its
threshold and otherwise uses qualifying pair inference. Each substitution is
recorded and the affine map reconstructs the original assignment. The existing
Warm Start QAOA runs only after reduction; it remains the existing local
statevector implementation and is capped at 20 variables. The 32-variable
four-customer cluster can therefore be reduced one measured variable at a time
to the 20-variable target. Smaller clusters are not padded.

As in the underlying approximate algorithms, measured relations do not guarantee
that any original feasible route remains in the reduced subspace. The pipeline
searches for a feasible Warm Start initializer only after reduction and reports
an error if no feasible assignment is reconstructable; it does not alter or
repair the QAOA-selected reductions.

Run the new API from the backend's existing Flask server:

```bash
curl -X POST http://127.0.0.1:5000/api/research/run \
  -H 'Content-Type: application/json' \
  -d '{"n_clusters": 4, "target_variables": 20, "reduction_method": "rqaoa", "shots": 2048}'
```

Set `reduction_method` to `qiro` to run QIRO instead. The response and
`backend/output/` artifacts include `results.json`, `assignments.json`,
`reduction_history.json`, `qaoa_history.json` (shot counts, expectations,
correlation matrices and counts), and `experiment_log.json`. Correlation
matrices contain the measured `<ZiZj>` estimates for every active pair at each
reduction step. IBM hardware submissions are disabled for this pipeline.

The CLI equivalent is `python main.py --research-pipeline --reduction-method rqaoa`.
Use `--reduction-method qiro` to select QIRO and `--shots` to set the Aer shot
count. The legacy hardware and advantage demonstrations elsewhere in this
README are separate from this simulator-only research pipeline.

Focused validation:

```bash
cd backend
python -m pytest tests
```

---

## 🎯 Problem Statement

The **Vehicle Routing Problem (VRP)** is a fundamental NP-Hard combinatorial optimization problem at the heart of global logistics. For a supply chain with *N* customers, the number of valid delivery routes scales as **O(N!)** — factorial growth that makes exact classical solutions computationally intractable beyond ~30 nodes.

Modern supply chains add further complexity: multi-modal vehicle fleets, supplier reliability scoring, warehouse inventory constraints, delivery deadlines, and real-time risk factors. Classical heuristics (Nearest Neighbour, Christofides) solve these sub-problems **sequentially and in isolation** — each step is locally optimal but globally blind, leading to significant cost inefficiency.

---

##  Goal

We built a **end-to-end Quantum VRP pipeline** that:

1. **Encodes** the full supply chain (suppliers → warehouses → customers) as a **QUBO (Quadratic Unconstrained Binary Optimization)** problem
2. **Maps** the QUBO onto a quantum Hamiltonian executed via **QAOA** (Quantum Approximate Optimization Algorithm)
3. **Deploys** the quantum circuit to IBM's 156-qubit **`ibm_fez`** superconducting processor — a real physical quantum computer
4. **Benchmarks** quantum hardware results against a unified classical MILP (Mixed-Integer Linear Programming) solver
5. **Visualizes** the full pipeline through an interactive React dashboard

---

##  Key Results

- ✅ Successfully encoded a 16-qubit (4-customer) VRP as a QUBO Hamiltonian. Hence showing how to encode a real-world end-to-end supply chain optimization problem into a quantum circuit which a quantum computer can understand and solve efficiently by mapping it to a Hamiltonian. 
- ✅ Submitted and executed the quantum circuit on **`ibm_fez`** (Job ID: `d84c4k80bvlc73d4dg9g`).   Demonstrating executing QAOA on real quantum hardware, and getting the same result we got from our classical simulator. Proving that quantum computers are capable of solving real-world optimization problems. Which would have a real world impact in fault-tolerant era, where optimization problems supercomputers cannot possibly solved can be attempted with quantum computers.
- ✅ Decoded quantum bitstring output into a physical supply chain route
- ✅ Demonstrated that the Unified MILP achieves **15.1% cost reduction** over the sequential pipeline. 
- ✅ Demonstrated that the classical "scaling wall" hits at ~28–35 nodes. Showcasing that even near term fault tolerant quantum computers will start to give an advantage over classical computers in optimization problems.
---


##  Project Structure

```
QuantumHackathon/
├── backend/                   # Python optimization engine
│   ├── app.py                 # Flask REST API (serves data to frontend)
│   ├── main.py                # Classical MILP pipeline entrypoint
│   ├── submit_job_ibm.py      # Submit QAOA job to IBM Quantum hardware
│   ├── fetch_job_ibm.py       # Fetch & decode IBM Quantum job results
│   ├── scaling_demo.py        # Classical wall demonstration script
│   ├── demo_advantage.py      # Quantum algorithmic advantage demo
│   ├── classical/             # MILP VRP solver module
│   ├── quantum/               # QAOA / QUBO formulation module
│   ├── graph/                 # Supply chain network builder (NetworkX)
│   ├── data/                  # Real supply chain dataset (CSVs)
│   └── requirements.txt       # Python dependencies
│
└── frontend/                  # React + Vite interactive dashboard
    ├── src/
    │   ├── pages/
    │   │   ├── Home.jsx            # Cinematic landing (scroll animation + team photo)
    │   │   ├── Dashboard.jsx       # Problem statement + scaling graph
    │   │   ├── ClassicalArchitecture.jsx  # Interactive network graph + MILP comparison
    │   │   ├── QuantumAdvantage.jsx       # Energy landscape + superposition explorer
    │   │   └── Comparison.jsx            # Quantum vs classical at scale
    │   ├── components/
    │   │   └── ScrollHero.jsx      # Scroll-driven canvas animation (192 frames)
    │   └── App.jsx                 # React Router setup
    └── public/
        ├── scrolleffect2/          # 192-frame quantum animation (WebP)
        └── group-photo.jpeg        # Team photo
```
## Our demo video and the Project ppt are in the frontend itself.
---

##  Running Locally

### Prerequisites
- Python ≥ 3.10
- Node.js ≥ 18

### 1. Backend (Flask API + Python scripts)

```bash
cd backend
pip install -r requirements.txt

# Start the Flask API server
python3 app.py
# Runs on http://127.0.0.1:5000
```

To run the classical optimizer standalone:
```bash
python3 main.py
```

To run the quantum advantage demonstration (local statevector simulator):
```bash
python3 demo_advantage.py
```

To benchmark the classical scaling wall:
```bash
python3 scaling_demo.py
```

### 2. Frontend (React Dashboard)

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

Open **http://localhost:5173** in your browser. Make sure the Flask backend is running first.

---

## IBM Quantum Hardware Pipeline

This project ran a real quantum circuit on IBM's 156-qubit **`ibm_fez`** superconducting processor.

### Submitting a New Job

```bash
cd backend
python3 submit_job_ibm.py
```

This will:
1. Authenticate with IBM Quantum via your API key
2. Pre-optimize QAOA parameters locally using a statevector simulator
3. Transpile the circuit for the `ibm_fez` backend
4. Submit the job and print the **Job ID** (save this!)

### Fetching Results

```bash
python fetch_job_ibm.py <JOB_ID>
# Example:
python fetch_job_ibm.py d84c4k80bvlc73d4dg9g
```

This will:
1. Retrieve the job from IBM Quantum
2. Decode the highest-probability bitstring into a physical supply chain route
3. Run the classical heuristic on the same subset
4. Print a side-by-side comparison

---

##  IBM Quantum API Key Setup


### Getting Your API Key
1. Sign up / log in at **https://quantum.ibm.com**
2. Go to **Account** → **API Token** → copy your token
3. You can view job status, circuit diagrams, and execution results at **https://quantum.ibm.com/jobs**

### Setting the Key
Use the environment variable for the research pipeline; do not put API tokens in
source files:

```bash
export IBM_QUANTUM_API_KEY="your_key_here"
```

The legacy `submit_job_ibm.py` and `fetch_job_ibm.py` scripts are separate from
the gated research pipeline above.

### Viewing Your Jobs on the IBM Dashboard
1. Go to **https://quantum.ibm.com/jobs**
2. Find your job by ID (printed when you run `submit_job_ibm.py`)
3. Click the job to see:
   - **Circuit diagram** — the QAOA ansatz transpiled for `ibm_fez`
   - **Transpilation details** — qubit mapping, gate depth, 2-qubit gate count
   - **Result histogram** — shot distribution across all measured bitstrings
   - **Queue status** — estimated wait time and execution time

---

##  Key Technical Concepts

| Concept | Description |
|---|---|
| **QUBO** | Quadratic Unconstrained Binary Optimization — maps VRP constraints to a binary energy landscape |
| **QAOA** | Quantum Approximate Optimization Algorithm — variational quantum circuit that finds the ground state (minimum cost) |
| **NISQ** | Noisy Intermediate-Scale Quantum — current era where decoherence limits circuit depth |
| **Decoherence** | Quantum state collapse due to environmental noise; our 681-gate circuit exceeds current coherence limits |
| **Hilbert Space** | The 2^N dimensional space of all possible routes explored simultaneously in quantum superposition |
| **ibm_fez** | IBM's 156-qubit Eagle r3 superconducting processor used in this project |

---

## Quantum Optimizers

I will approximately explain the distinctin between quantum optmizers and classical optmizer 

**Classical**
Optimizer will walk in one random direction at a time and check the elevation and if its higher then go back, if it lower or same elevation take the next random directional step

**Quantum Optimizer**
Optimizer will take a step in every direction simultaneously, keep doing this repeatedly. At the end of the walk the amongst all the path simultaneously taken, the one that connect initial point to the lowest point becomes the most likely outcome upon called measurement (called state collapse in Quantum mechanics). The way it does is different upon the optimization algorithm used. 
QAOA  : The Quantum Approximate Optimization Algorithm (QAOA) is a hybrid quantum-classical algorithm designed to find  approximate solutions to combinatorial optimization problems, which are often NP-	   hard and computationally challenging for classical computers to solve exactly. QAOA leverages quantum phenomena such as superposition and entanglement to explore large solution spaces more 	   efficiently than classical heuristics. "https://pennylane.ai/qml/demos/tutorial_qaoa_intro"
