"""
Generates synthetic supply chain data and saves as CSVs.
Run once to bootstrap: python -m data.generate_data
"""

import os
import numpy as np
import pandas as pd

np.random.seed(42)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Entity generators
# ---------------------------------------------------------------------------

def generate_suppliers(n=8):
    return pd.DataFrame({
        "supplier_id":       [f"S{i+1}" for i in range(n)],
        "name":              [f"Supplier_{i+1}" for i in range(n)],
        "lat":               np.random.uniform(18.0, 28.0, n).round(4),
        "lon":               np.random.uniform(72.0, 88.0, n).round(4),
        "capacity":          np.random.randint(500, 2000, n),
        "cost_per_unit":     np.random.uniform(10, 50, n).round(2),
        "lead_time_days":    np.random.randint(1, 15, n),
        "reliability_score": np.random.uniform(0.70, 1.00, n).round(2),
        "is_active":         [True] * n,
    })


def generate_warehouses(n=5):
    return pd.DataFrame({
        "warehouse_id":          [f"W{i+1}" for i in range(n)],
        "name":                  [f"Warehouse_{i+1}" for i in range(n)],
        "lat":                   np.random.uniform(20.0, 26.0, n).round(4),
        "lon":                   np.random.uniform(74.0, 86.0, n).round(4),
        "storage_capacity":      np.random.randint(1000, 5000, n),
        "holding_cost_per_unit": np.random.uniform(1.0, 5.0, n).round(2),
        "fixed_cost":            np.random.randint(1000, 5000, n),
    })


def generate_vehicles(n=15, warehouse_ids=None):
    if warehouse_ids is None:
        warehouse_ids = [f"W{i+1}" for i in range(5)]
    return pd.DataFrame({
        "vehicle_id":    [f"V{i+1}" for i in range(n)],
        "type":          np.random.choice(["Truck", "Van", "Bike"], n),
        "capacity_kg":   np.random.choice([500, 1000, 2000, 5000], n),
        "cost_per_km":   np.random.uniform(5, 20, n).round(2),
        "speed_kmph":    np.random.randint(30, 80, n),
        "warehouse_id":  np.random.choice(warehouse_ids, n),
    })


def generate_customers(n=10):
    return pd.DataFrame({
        "customer_id":           [f"C{i+1}" for i in range(n)],
        "name":                  [f"Customer_{i+1}" for i in range(n)],
        "lat":                   np.random.uniform(19.0, 27.0, n).round(4),
        "lon":                   np.random.uniform(73.0, 87.0, n).round(4),
        "demand_units":          np.random.randint(50, 300, n),
        "priority":              np.random.choice(["High", "Medium", "Low"], n),
        "delivery_deadline_days": np.random.randint(2, 10, n),
    })


def generate_routes(suppliers, warehouses, customers, max_dist_km=800):
    """Build route edges between every pair of nodes within max_dist_km."""
    nodes = (
        [(r.supplier_id, r.lat, r.lon) for r in suppliers.itertuples()]
        + [(r.warehouse_id, r.lat, r.lon) for r in warehouses.itertuples()]
        + [(r.customer_id, r.lat, r.lon) for r in customers.itertuples()]
    )

    rows = []
    for i, (sid, slat, slon) in enumerate(nodes):
        for j, (did, dlat, dlon) in enumerate(nodes):
            if sid == did:
                continue
            dist = haversine(slat, slon, dlat, dlon)
            if dist <= max_dist_km:
                rows.append({
                    "from_node":      sid,
                    "to_node":        did,
                    "distance_km":    round(dist, 2),
                    "cost_per_km":    round(np.random.uniform(8, 18), 2),
                    "travel_time_hrs": round(dist / 60, 2),
                })
    return pd.DataFrame(rows)


def generate_inventory(suppliers, warehouses):
    rows = []
    for w in warehouses.itertuples():
        for s in suppliers.itertuples():
            rows.append({
                "warehouse_id":   w.warehouse_id,
                "supplier_id":    s.supplier_id,
                "current_stock":  np.random.randint(0, 500),
                "reorder_point":  np.random.randint(50, 150),
                "order_quantity": np.random.randint(100, 400),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(out_dir="data"):
    os.makedirs(out_dir, exist_ok=True)

    suppliers  = generate_suppliers()
    warehouses = generate_warehouses()
    vehicles   = generate_vehicles(warehouse_ids=warehouses["warehouse_id"].tolist())
    customers  = generate_customers()
    inventory  = generate_inventory(suppliers, warehouses)
    routes     = generate_routes(suppliers, warehouses, customers)

    suppliers.to_csv(f"{out_dir}/suppliers.csv",   index=False)
    warehouses.to_csv(f"{out_dir}/warehouses.csv", index=False)
    vehicles.to_csv(f"{out_dir}/vehicles.csv",     index=False)
    customers.to_csv(f"{out_dir}/customers.csv",   index=False)
    inventory.to_csv(f"{out_dir}/inventory.csv",   index=False)
    routes.to_csv(f"{out_dir}/routes.csv",         index=False)

    print("✅  Data generated successfully")
    print(f"   Suppliers  : {len(suppliers)}")
    print(f"   Warehouses : {len(warehouses)}")
    print(f"   Vehicles   : {len(vehicles)}")
    print(f"   Customers  : {len(customers)}")
    print(f"   Routes     : {len(routes)}")
    print(f"   Inventory  : {len(inventory)} records")


if __name__ == "__main__":
    main()
