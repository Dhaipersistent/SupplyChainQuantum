import pandas as pd

from app import app


def test_existing_dashboard_api_payload_shapes_remain_available():
    client = app.test_client()

    scaling = client.get("/api/scaling_data")
    overview = client.get("/api/dataset_overview")

    assert scaling.status_code == 200
    assert isinstance(scaling.get_json(), list)
    assert {"nodes", "classical_time", "qaoa_time"} <= set(scaling.get_json()[0])
    assert overview.status_code == 200
    payload = overview.get_json()
    assert {"counts", "suppliers", "warehouses", "customers"} <= set(payload)
    assert "customers" in payload["counts"]


def test_research_results_endpoint_returns_artifact_schema():
    client = app.test_client()

    response = client.get("/api/research/results")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["available"], bool)
    assert isinstance(payload["results"], list)
    assert isinstance(payload["reduction_history"], list)


def test_research_run_dispatches_requested_reduction_method(monkeypatch):
    from outer_layer import improvement_loop

    graph = type(
        "GraphFixture",
        (),
        {
            "customers": pd.DataFrame({"customer_id": ["customer-1"]}),
            "warehouses": pd.DataFrame({"warehouse_id": ["warehouse-1", "warehouse-2"]}),
            "vehicles": pd.DataFrame({"warehouse_id": ["warehouse-1", "warehouse-2"]}),
        },
    )()
    monkeypatch.setattr("app.SupplyChainGraph", lambda data_dir: graph)
    called = {}

    def fake_run(customers, warehouses, vehicles, **options):
        called.update(options)
        return {"results": [], "reduction_method": options["reduction_method"]}

    monkeypatch.setattr(improvement_loop, "run_improvement_loop", fake_run)
    response = app.test_client().post(
        "/api/research/run",
        json={
            "n_clusters": 1,
            "target_variables": 20,
            "reduction_method": "qiro",
            "shots": 2048,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["reduction_method"] == "qiro"
    assert called["reduction_method"] == "qiro"
    assert called["shots"] == 2048
    assert called["output_dir"].endswith("/backend/output")
