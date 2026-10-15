import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from graph.network_builder import SupplyChainGraph
from classical.vrp_solver import VRPSolver

app = Flask(__name__)
CORS(app)


def _data_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@app.route('/api/network')
def get_network():
    sc = SupplyChainGraph(data_dir=_data_path())
    nodes = []
    edges = []
    
    for n, d in sc.G.nodes(data=True):
        nodes.append({
            "id": n,
            "type": d.get("type", "unknown"),
            "lat": d.get("lat", 0),
            "lon": d.get("lon", 0),
        })
        
    for u, v, d in sc.G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "distance": d.get("distance", 0)
        })
        
    return jsonify({"nodes": nodes, "edges": edges})

@app.route('/api/shipment_plan')
def get_shipment_plan():
    sc = SupplyChainGraph(data_dir=_data_path())
    vrp = VRPSolver(sc.warehouses, sc.customers, sc.vehicles, sc.routes)
    res = vrp.solve()
    
    routes = []
    for r in res['routes_df'].itertuples():
        # Get vehicle base cost
        v_df = sc.vehicles[sc.vehicles['vehicle_id'] == r.vehicle_id]
        v_type = v_df.iloc[0]['type'] if not v_df.empty else "Unknown"
        
        # Calculate units (demand satisfied)
        # Parse route nodes
        route_nodes = [n.strip() for n in r.route.split("→")]
        units = 0
        for n in route_nodes:
            c_df = sc.customers[sc.customers['customer_id'] == n]
            if not c_df.empty:
                units += c_df.iloc[0]['demand_units']
                
        routes.append({
            "vehicle_id": r.vehicle_id,
            "vehicle_type": v_type,
            "source_warehouse": r.warehouse_id,
            "path": r.route,
            "distance_km": round(r.distance_km, 2),
            "units_delivered": int(units)
        })
        
    return jsonify({
        "total_cost": round(res['total_cost'], 2),
        "total_distance": round(res['total_distance_km'], 2),
        "routes": routes
    })

@app.route('/api/scaling_data')
def get_scaling_data():
    # ─── Modeled Execution Time Scaling ─────────────────────────
    # X-axis: Problem Size N (nodes)
    # Y-axis: Execution Time (seconds)
    #
    # 1. Classical Exact (Held-Karp): Time ~ O(2^N * N^2)
    #    We model an operation taking ~10 nanoseconds (1e-8 s).
    # 2. QAOA (ibm_fez): Time ~ QPU network overhead + Gate time scaling
    #    Circuit depth ~ O(N^2.5). Base execution overhead ~ 5 seconds.
    #    Pulse overhead coefficient ~ 0.005 seconds per N^2.5 tier.
    
    nodes = [5, 10, 15, 20, 25, 28, 30, 35, 40]
    c1 = 1e-8
    c2 = 0.005
    qpu_base = 5.0
    
    data = []
    for n in nodes:
        # Classical time grows exponentially
        c_time = (2**n * n**2) * c1
        # Log scales cannot handle 0. Ensure a small baseline for visibility
        c_time_display = max(min(c_time, 1000000.0), 1e-6)
        
        # QAOA time grows slowly
        q_time = qpu_base + (n**2.5) * c2
        
        data.append({
            "nodes": n,
            "classical_time": round(c_time_display, 6),
            "qaoa_time": round(q_time, 2)
        })
    return jsonify(data)

@app.route('/api/dataset_overview')
def get_dataset_overview():
    sc = SupplyChainGraph(data_dir=_data_path())

    suppliers = []
    for r in sc.suppliers.itertuples():
        suppliers.append({
            "id": r.supplier_id,
            "capacity": int(r.capacity),
            "cost_per_unit": float(r.cost_per_unit),
            "lead_time_days": int(r.lead_time_days),
            "reliability": float(r.reliability_score),
        })

    warehouses = []
    for r in sc.warehouses.itertuples():
        warehouses.append({
            "id": r.warehouse_id,
            "storage_capacity": int(r.storage_capacity),
            "holding_cost": float(r.holding_cost_per_unit),
        })

    customers = []
    for r in sc.customers.itertuples():
        customers.append({
            "id": r.customer_id,
            "demand_units": int(r.demand_units),
            "priority": r.priority,
            "deadline_days": int(r.delivery_deadline_days),
        })

    return jsonify({
        "counts": {
            "suppliers": len(suppliers),
            "warehouses": len(warehouses),
            "customers": len(customers),
            "vehicles": len(sc.vehicles),
            "routes": len(sc.routes),
        },
        "suppliers": suppliers[:7],
        "warehouses": warehouses[:5],
        "customers": customers[:8],
    })


@app.route('/api/research/run', methods=['POST'])
def run_research_pipeline():
    options = request.get_json(silent=False) or {}
    if not isinstance(options, dict):
        return jsonify({"error": "JSON body must be an object"}), 400
    n_clusters = options.get("n_clusters", 4)
    target_variables = options.get("target_variables", 20)
    reduction_method = options.get("reduction_method", "rqaoa")
    shots = options.get("shots", 2048)
    qiro_expectation_threshold = options.get("qiro_expectation_threshold", 0.05)
    run_hardware = options.get("run_hardware", False)
    if not isinstance(n_clusters, int) or isinstance(n_clusters, bool):
        return jsonify({"error": "n_clusters must be an integer"}), 400
    if not isinstance(target_variables, int) or isinstance(target_variables, bool):
        return jsonify({"error": "target_variables must be an integer"}), 400
    if reduction_method not in {"rqaoa", "qiro"}:
        return jsonify({"error": "reduction_method must be 'rqaoa' or 'qiro'"}), 400
    if not isinstance(shots, int) or isinstance(shots, bool) or shots < 1:
        return jsonify({"error": "shots must be a positive integer"}), 400
    if (
        isinstance(qiro_expectation_threshold, bool)
        or not isinstance(qiro_expectation_threshold, (int, float))
        or not 0 < qiro_expectation_threshold <= 1
    ):
        return jsonify({"error": "qiro_expectation_threshold must be in (0, 1]"}), 400
    if not isinstance(run_hardware, bool):
        return jsonify({"error": "run_hardware must be a boolean"}), 400
    if run_hardware:
        return jsonify({"error": "IBM hardware is disabled; this pipeline uses Aer Simulator only"}), 400
    sc = SupplyChainGraph(data_dir=_data_path())
    customer_count = len(sc.customers)
    warehouse_count = len(sc.warehouses)
    if not 1 <= n_clusters <= customer_count:
        return jsonify({"error": f"n_clusters must be between 1 and {customer_count}"}), 400
    if not 1 <= target_variables <= 20:
        return jsonify({"error": "target_variables must be between 1 and 20"}), 400
    if warehouse_count < 2:
        return jsonify({"error": "At least two warehouses are required"}), 400

    from outer_layer.improvement_loop import run_improvement_loop

    result = run_improvement_loop(
        sc.customers,
        sc.warehouses,
        sc.vehicles,
        n_clusters=n_clusters,
        target_variables=target_variables,
        reduction_method=reduction_method,
        shots=shots,
        qiro_expectation_threshold=float(qiro_expectation_threshold),
        output_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"),
    )
    return jsonify(result)


@app.route('/api/research/results', methods=['GET'])
def get_research_results():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    payload = {"available": False}
    for filename in (
        "results.json",
        "assignments.json",
        "reduction_history.json",
        "qaoa_history.json",
        "experiment_log.json",
    ):
        path = os.path.join(output_path, filename)
        if not os.path.isfile(path):
            payload[filename.removesuffix(".json")] = []
            continue
        with open(path, encoding="utf-8") as result_file:
            payload[filename.removesuffix(".json")] = json.load(result_file)
            payload["available"] = True
    return jsonify(payload)


if __name__ == '__main__':
    app.run(port=5000, debug=True)
