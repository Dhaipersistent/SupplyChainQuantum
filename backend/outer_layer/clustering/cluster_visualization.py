from pathlib import Path

import pandas as pd


def save_cluster_plot(
    customers: pd.DataFrame,
    centroids: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Save a latitude/longitude scatter plot; matplotlib is loaded on demand."""
    import matplotlib.pyplot as plt

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(8, 6))
    for cluster_id, members in customers.groupby("cluster_id", sort=True):
        axis.scatter(members["lon"], members["lat"], label=f"Cluster {cluster_id}")
    axis.scatter(
        centroids["centroid_lon"],
        centroids["centroid_lat"],
        marker="x",
        s=100,
        linewidths=2,
        color="black",
        label="Centroids",
    )
    axis.set(xlabel="Longitude", ylabel="Latitude", title="Customer clusters")
    axis.legend()
    fig.tight_layout()
    fig.savefig(destination)
    plt.close(fig)
    return destination
