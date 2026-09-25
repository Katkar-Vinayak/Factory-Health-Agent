"""
Automatic Machine Data Synchronization Utility
Detects new machines added to backend/data/machine_metadata.csv
and generates the corresponding sensor telemetry, production logs,
and maintenance history to keep all datasets fully synchronized.

Usage:
    cd backend/data
    python sync_machine_data.py

Followed by retraining the ML models:
    python ../ml/train_models.py
"""

import os
import sys
import pandas as pd

# Add current directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from generate_dataset import generate_all_datasets, DATA_DIR, METADATA_PATH, SENSOR_PATH, PRODUCTION_PATH, MAINTENANCE_PATH


def sync_machine_datasets(force=False):
    """
    Checks if any machines in machine_metadata.csv lack telemetry or production data.
    If detected (or if force=True), synchronizes all datasets.
    """
    print("\n--- CHECKING MACHINE CATALOG SYNCHRONIZATION ---")
    if not os.path.exists(METADATA_PATH):
        print(f"Error: Authoritative catalog not found at {METADATA_PATH}")
        sys.exit(1)

    df_meta = pd.read_csv(METADATA_PATH, keep_default_na=False)
    for col in df_meta.select_dtypes(include='object').columns:
        df_meta[col] = df_meta[col].astype(str).str.strip()
    catalog_machines = set(df_meta['machine_id'].unique())
    print(f"Authoritative machine catalog ({len(catalog_machines)} machines): {sorted(list(catalog_machines))}")

    sensor_machines = set()
    if os.path.exists(SENSOR_PATH):
        df_sensor = pd.read_csv(SENSOR_PATH, usecols=['machine_id'])
        sensor_machines = set(df_sensor['machine_id'].unique())

    prod_machines = set()
    if os.path.exists(PRODUCTION_PATH):
        df_prod = pd.read_csv(PRODUCTION_PATH, usecols=['machine_id'])
        prod_machines = set(df_prod['machine_id'].unique())

    missing_sensor = catalog_machines - sensor_machines
    missing_prod = catalog_machines - prod_machines
    missing_any = missing_sensor | missing_prod

    if not missing_any and not force:
        print(f"All {len(catalog_machines)} machines are already fully synchronized across all datasets.")
        print("No new machine telemetry generation required.")
        return False

    if missing_any:
        print(f"\n[!] Detected {len(missing_any)} machine(s) requiring synchronization: {sorted(list(missing_any))}")
        if missing_sensor:
            print(f"    - Missing in sensor_data.csv: {sorted(list(missing_sensor))}")
        if missing_prod:
            print(f"    - Missing in production_logs.csv: {sorted(list(missing_prod))}")

    print("\nRunning dataset synchronization pipeline...")
    df_machines, df_sensor, df_maint, df_prod = generate_all_datasets(data_dir=DATA_DIR)

    print("\n[SUCCESS] Datasets synchronized successfully.")
    print(f"Total synchronized machines: {df_sensor['machine_id'].nunique()}")
    print("\nRECOMMENDED NEXT STEP:")
    print("Run the model retraining script so ML models learn the updated telemetry:")
    print("    python ../ml/train_models.py")
    return True


if __name__ == '__main__':
    force_sync = '--force' in sys.argv
    sync_machine_datasets(force=force_sync)
