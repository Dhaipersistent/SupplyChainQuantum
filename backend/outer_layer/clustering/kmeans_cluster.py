from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


@dataclass(frozen=True)
class ClusterResult:
    customers: pd.DataFrame
    centroids: pd.DataFrame


def cluster_customers(
    customers: pd.DataFrame,
    n_clusters: int = 4,
    random_state: int = 42,
) -> ClusterResult:
    """Assign customers to geographic clusters and return their centroids."""
    required = {"customer_id", "lat", "lon"}
    missing = required.difference(customers.columns)
    if missing:
        raise ValueError(f"Customer data is missing columns: {sorted(missing)}")
    if customers.empty or n_clusters < 1 or n_clusters > len(customers):
        raise ValueError("n_clusters must be between 1 and the number of customers")
    if customers["customer_id"].duplicated().any():
        raise ValueError("customer_id values must be unique")

    coordinates = customers[["lat", "lon"]].to_numpy(dtype=float)
    if not np.isfinite(coordinates).all():
        raise ValueError("Customer coordinates must be finite")
    if ((coordinates[:, 0] < -90) | (coordinates[:, 0] > 90)).any():
        raise ValueError("Latitude must be between -90 and 90")
    if ((coordinates[:, 1] < -180) | (coordinates[:, 1] > 180)).any():
        raise ValueError("Longitude must be between -180 and 180")

    mean_latitude = np.deg2rad(coordinates[:, 0].mean())
    projected = coordinates.copy()
    projected[:, 1] *= np.cos(mean_latitude)
    labels = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10).fit_predict(projected)
    if np.unique(labels).size != n_clusters:
        raise ValueError("KMeans found fewer distinct clusters than requested; check for duplicate coordinates")

    result = customers.copy()
    result["cluster_id"] = labels
    centroid_rows = []
    for label, members in result.groupby("cluster_id", sort=True):
        centroid_rows.append(
            {
                "cluster_id": int(label),
                "centroid_lat": float(members["lat"].mean()),
                "centroid_lon": float(members["lon"].mean()),
                "customer_count": int(len(members)),
            }
        )
    centroids = pd.DataFrame(centroid_rows).sort_values(
        ["centroid_lat", "centroid_lon"], ignore_index=True
    )
    stable_labels = {old: new for new, old in enumerate(centroids["cluster_id"].tolist())}
    result["cluster_id"] = result["cluster_id"].map(stable_labels).astype(int)
    centroids["cluster_id"] = range(len(centroids))
    result = result.sort_values(["cluster_id", "customer_id"], ignore_index=True)
    return ClusterResult(customers=result, centroids=centroids)
