import pandas as pd
import pytest

from outer_layer.clustering.kmeans_cluster import cluster_customers
from outer_layer.distance_matrix import build_distance_matrix, haversine_km


def test_kmeans_clusters_customers_and_returns_centroids():
    customers = pd.DataFrame(
        {
            "customer_id": ["a", "b", "c", "d"],
            "lat": [0.0, 0.1, 20.0, 20.1],
            "lon": [0.0, 0.1, 20.0, 20.1],
        }
    )

    result = cluster_customers(customers, n_clusters=2)

    assert result.customers["cluster_id"].nunique() == 2
    assert result.centroids["customer_count"].sum() == 4
    assert result.centroids[["centroid_lat", "centroid_lon"]].notna().all().all()


def test_clustering_rejects_too_many_clusters():
    customers = pd.DataFrame({"customer_id": ["a"], "lat": [0.0], "lon": [0.0]})

    with pytest.raises(ValueError, match="n_clusters"):
        cluster_customers(customers, n_clusters=2)


def test_distance_matrix_is_symmetric_and_zero_on_diagonal():
    points = pd.DataFrame({"id": ["a", "b"], "lat": [0.0, 0.0], "lon": [0.0, 1.0]})

    matrix = build_distance_matrix(points)

    assert matrix.loc["a", "a"] == 0
    assert matrix.loc["a", "b"] == pytest.approx(matrix.loc["b", "a"])
    assert matrix.loc["a", "b"] == pytest.approx(haversine_km(0, 0, 0, 1))
