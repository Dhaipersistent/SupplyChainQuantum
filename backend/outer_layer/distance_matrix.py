from __future__ import annotations

import numpy as np
import pandas as pd


EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    values = np.asarray([lat1, lon1, lat2, lon2], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Coordinates must be finite")
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = np.deg2rad(values)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    a = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    )
    return float(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0))))


def build_distance_matrix(points: pd.DataFrame, id_column: str = "id") -> pd.DataFrame:
    """Build a symmetric great-circle distance matrix from records with lat/lon."""
    required = {id_column, "lat", "lon"}
    missing = required.difference(points.columns)
    if missing:
        raise ValueError(f"Point data is missing columns: {sorted(missing)}")
    if points[id_column].duplicated().any():
        raise ValueError(f"{id_column} values must be unique")
    ids = points[id_column].tolist()
    coordinates = points[["lat", "lon"]].to_numpy(dtype=float)
    if not np.isfinite(coordinates).all():
        raise ValueError("Point coordinates must be finite")
    matrix = np.zeros((len(ids), len(ids)), dtype=float)
    for left in range(len(ids)):
        for right in range(left + 1, len(ids)):
            distance = haversine_km(*coordinates[left], *coordinates[right])
            matrix[left, right] = matrix[right, left] = distance
    return pd.DataFrame(matrix, index=ids, columns=ids)


def nearest_warehouses(
    centroid: pd.Series,
    warehouses: pd.DataFrame,
    count: int = 2,
) -> list[str]:
    """Return warehouse IDs closest to a centroid, with stable tie ordering."""
    required = {"warehouse_id", "lat", "lon"}
    missing = required.difference(warehouses.columns)
    if missing:
        raise ValueError(f"Warehouse data is missing columns: {sorted(missing)}")
    if count < 1 or count > len(warehouses):
        raise ValueError("count must be between 1 and the number of warehouses")
    ranked = warehouses.assign(
        _distance=warehouses.apply(
            lambda row: haversine_km(
                float(centroid["centroid_lat"]),
                float(centroid["centroid_lon"]),
                float(row["lat"]),
                float(row["lon"]),
            ),
            axis=1,
        )
    ).sort_values(["_distance", "warehouse_id"], kind="stable")
    return ranked["warehouse_id"].head(count).astype(str).tolist()
