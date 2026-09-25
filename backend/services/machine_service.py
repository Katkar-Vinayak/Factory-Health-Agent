import os
import sys
import re
import csv
import threading
import subprocess
import pandas as pd
from typing import List, Dict, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Concurrency lock for machine onboarding
_add_machine_lock = threading.Lock()

# Dynamic cache tracking for datasets
_last_sensors_mtime = 0.0
_cached_df_sensors: Optional[pd.DataFrame] = None

_last_maintenance_mtime = 0.0
_cached_df_maintenance: Optional[pd.DataFrame] = None

_last_production_mtime = 0.0
_cached_df_production: Optional[pd.DataFrame] = None


def get_sensors_df() -> pd.DataFrame:
    global _last_sensors_mtime, _cached_df_sensors
    sensors_path = os.path.join(DATA_DIR, 'sensor_data.csv')
    try:
        current_mtime = os.path.getmtime(sensors_path)
        if _cached_df_sensors is None or current_mtime != _last_sensors_mtime:
            df = pd.read_csv(sensors_path, keep_default_na=False)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            _cached_df_sensors = df
            _last_sensors_mtime = current_mtime
    except Exception:
        if _cached_df_sensors is None:
            _cached_df_sensors = pd.read_csv(sensors_path, keep_default_na=False)
    return _cached_df_sensors


def get_maintenance_df() -> pd.DataFrame:
    global _last_maintenance_mtime, _cached_df_maintenance
    maint_path = os.path.join(DATA_DIR, 'maintenance_records.csv')
    try:
        current_mtime = os.path.getmtime(maint_path)
        if _cached_df_maintenance is None or current_mtime != _last_maintenance_mtime:
            df = pd.read_csv(maint_path, keep_default_na=False)
            if 'maintenance_date' in df.columns:
                df['maintenance_date'] = pd.to_datetime(df['maintenance_date'])
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            _cached_df_maintenance = df
            _last_maintenance_mtime = current_mtime
    except Exception:
        if _cached_df_maintenance is None:
            _cached_df_maintenance = pd.read_csv(maint_path, keep_default_na=False)
    return _cached_df_maintenance


def get_production_df() -> pd.DataFrame:
    global _last_production_mtime, _cached_df_production
    prod_path = os.path.join(DATA_DIR, 'production_logs.csv')
    try:
        current_mtime = os.path.getmtime(prod_path)
        if _cached_df_production is None or current_mtime != _last_production_mtime:
            df = pd.read_csv(prod_path, keep_default_na=False)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            _cached_df_production = df
            _last_production_mtime = current_mtime
    except Exception:
        if _cached_df_production is None:
            _cached_df_production = pd.read_csv(prod_path, keep_default_na=False)
    return _cached_df_production


def get_all_machines() -> List[Dict]:
    metadata_path = os.path.join(DATA_DIR, 'machine_metadata.csv')
    df = pd.read_csv(metadata_path, keep_default_na=False)
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip()
    return df.to_dict(orient='records')


def get_machine(machine_id: str) -> Optional[Dict]:
    metadata_path = os.path.join(DATA_DIR, 'machine_metadata.csv')
    df = pd.read_csv(metadata_path, keep_default_na=False)
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip()
    machine = df[df['machine_id'] == machine_id]
    if machine.empty:
        return None
    return machine.iloc[0].to_dict()


def generate_next_machine_id(metadata_path: str = None) -> str:
    """
    Determines next sequential machine ID from machine_metadata.csv.
    Extracts numeric portions from IDs matching M_<number>, finds max, and increments by 1.
    """
    if metadata_path is None:
        metadata_path = os.path.join(DATA_DIR, 'machine_metadata.csv')
    
    if not os.path.exists(metadata_path):
        return "M_001"

    df = pd.read_csv(metadata_path, keep_default_na=False)
    existing_ids = [str(x).strip() for x in df['machine_id'].dropna().unique()]
    
    numbers = []
    for mid in existing_ids:
        match = re.match(r'^M_(\d+)$', mid)
        if match:
            numbers.append(int(match.group(1)))

    next_num = max(numbers) + 1 if numbers else 1
    new_id = f"M_{next_num:03d}"
    
    # Guarantee no collision
    while new_id in existing_ids:
        next_num += 1
        new_id = f"M_{next_num:03d}"

    return new_id


def add_new_machine(machine_data: dict) -> dict:
    """
    Thread-safe workflow to:
    1. Acquire lock.
    2. Generate next sequential machine ID.
    3. Append exactly one row to machine_metadata.csv.
    4. Execute sync_machine_data.py to generate sensor telemetry, production logs, and maintenance records.
    5. Execute train_models.py to retrain ML models.
    6. Invalidate data caches and reload models.
    7. Return standardized response.
    """
    with _add_machine_lock:
        metadata_path = os.path.join(DATA_DIR, 'machine_metadata.csv')
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"machine_metadata.csv not found at {metadata_path}")

        # 1. Generate next ID
        machine_id = generate_next_machine_id(metadata_path)

        # 2. Prepare clean machine row
        new_machine_record = {
            'machine_id': machine_id,
            'machine_name': str(machine_data['machine_name']).strip(),
            'machine_type': str(machine_data['machine_type']).strip(),
            'machine_age_years': float(machine_data['machine_age_years']),
            'rated_power_kw': float(machine_data['rated_power_kw']),
            'installation_date': str(machine_data['installation_date']).strip(),
            'operating_hours': int(machine_data['operating_hours']),
            'maintenance_count': int(machine_data['maintenance_count']),
            'criticality_level': str(machine_data['criticality_level']).strip()
        }

        # 3. Append to machine_metadata.csv safely
        try:
            with open(metadata_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    new_machine_record['machine_id'],
                    new_machine_record['machine_name'],
                    new_machine_record['machine_type'],
                    new_machine_record['machine_age_years'],
                    new_machine_record['rated_power_kw'],
                    new_machine_record['installation_date'],
                    new_machine_record['operating_hours'],
                    new_machine_record['maintenance_count'],
                    new_machine_record['criticality_level']
                ])
        except Exception as e:
            raise RuntimeError(f"Failed writing to machine_metadata.csv: {str(e)}")

        # 4. Run automatic data synchronization
        sync_script = os.path.join(DATA_DIR, 'sync_machine_data.py')
        try:
            sync_proc = subprocess.run(
                [sys.executable, str(sync_script)],
                cwd=DATA_DIR,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception as e:
            raise RuntimeError(f"Failed to execute sync_machine_data.py: {str(e)}")

        if sync_proc.returncode != 0:
            err_msg = sync_proc.stderr.strip() or sync_proc.stdout.strip() or "Unknown synchronization failure"
            raise RuntimeError(f"Machine data synchronization failed: {err_msg}")

        # 5. Run automatic model retraining
        ml_dir = os.path.join(BASE_DIR, 'ml')
        train_script = os.path.join(ml_dir, 'train_models.py')
        try:
            train_proc = subprocess.run(
                [sys.executable, str(train_script)],
                cwd=ml_dir,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception as e:
            raise RuntimeError(f"Machine metadata added and synchronized, but model training invocation failed: {str(e)}")

        if train_proc.returncode != 0:
            err_msg = train_proc.stderr.strip() or train_proc.stdout.strip() or "Unknown model training failure"
            raise RuntimeError(f"Machine metadata was added and synchronized, but model retraining failed: {err_msg}")

        # 6. Invalidate memory caches so all endpoints immediately serve fresh data
        global _last_sensors_mtime, _cached_df_sensors
        global _last_maintenance_mtime, _cached_df_maintenance
        global _last_production_mtime, _cached_df_production
        _last_sensors_mtime = 0.0
        _cached_df_sensors = None
        _last_maintenance_mtime = 0.0
        _cached_df_maintenance = None
        _last_production_mtime = 0.0
        _cached_df_production = None

        # Force ml_service to reload latest trained models
        try:
            from services import ml_service
            ml_service.ml_service_instance._ensure_latest_models()
        except Exception:
            pass

        return {
            "success": True,
            "machine_id": machine_id,
            "machine": new_machine_record,
            "synchronization": {
                "success": True,
                "message": "Machine telemetry synchronized"
            },
            "training": {
                "success": True,
                "message": "ML models retrained"
            },
            "message": f"Machine {machine_id} added successfully"
        }


def get_latest_sensor_record(machine_id: str, timestamp: str = None, include_ground_truth: bool = False) -> Optional[Dict]:
    sensors_df = get_sensors_df()
    machine_sensors = sensors_df[sensors_df['machine_id'] == machine_id]
    if machine_sensors.empty:
        return None
    
    machine_sensors = machine_sensors.sort_values('timestamp')
    
    if timestamp:
        target_time = pd.to_datetime(timestamp)
        exact = machine_sensors[machine_sensors['timestamp'] == target_time]
        if not exact.empty:
            record = exact.iloc[0].to_dict()
        else:
            machine_sensors_copy = machine_sensors.copy()
            machine_sensors_copy['time_diff'] = (machine_sensors_copy['timestamp'] - target_time).abs()
            record = machine_sensors_copy.sort_values('time_diff').iloc[0].to_dict()
            del record['time_diff']
    else:
        record = machine_sensors.iloc[-1].to_dict()
        
    if 'timestamp' in record and pd.notnull(record['timestamp']):
        record['timestamp'] = str(record['timestamp'])

    if not include_ground_truth and 'failure_type' in record:
        del record['failure_type']

    return record


def get_sensor_history(machine_id: str, timestamp: str = None, limit: int = 10) -> List[Dict]:
    """
    Returns recent sensor records up to `timestamp` (or latest if timestamp is None),
    ordered chronologically (most recent last). Excludes ground-truth failure_type.
    """
    sensors_df = get_sensors_df()
    machine_sensors = sensors_df[sensors_df['machine_id'] == machine_id]
    if machine_sensors.empty:
        return []
    
    machine_sensors = machine_sensors.sort_values('timestamp')
    
    if timestamp:
        target_time = pd.to_datetime(timestamp)
        machine_sensors = machine_sensors[machine_sensors['timestamp'] <= target_time]

    records = machine_sensors.tail(limit).to_dict(orient='records')
    for r in records:
        if 'timestamp' in r and pd.notnull(r['timestamp']):
            r['timestamp'] = str(r['timestamp'])
        if 'failure_type' in r:
            del r['failure_type']

    return records


def get_energy_history(machine_id: str, timestamp: str = None, limit: int = 10) -> List[Dict]:
    """
    Returns recent energy consumption and load records for machine_id up to `timestamp`.
    """
    history = get_sensor_history(machine_id, timestamp, limit=limit)
    energy_records = []
    for r in history:
        energy_records.append({
            'timestamp': r.get('timestamp'),
            'machine_id': r.get('machine_id'),
            'energy_consumption_kwh': r.get('energy_consumption_kwh'),
            'load_percent': r.get('load_percent'),
            'ambient_temperature_c': r.get('ambient_temperature_c')
        })
    return energy_records


def get_machine_maintenance_history(machine_id: str, timestamp: str = None) -> List[Dict]:
    """
    Returns maintenance records for machine_id up to `timestamp` if specified.
    """
    maintenance_df = get_maintenance_df()
    machine_maintenance = maintenance_df[maintenance_df['machine_id'] == machine_id]
    if machine_maintenance.empty:
        return []

    date_col = 'maintenance_date' if 'maintenance_date' in machine_maintenance.columns else 'date'
    machine_maintenance = machine_maintenance.sort_values(date_col)

    if timestamp:
        target_time = pd.to_datetime(timestamp)
        machine_maintenance = machine_maintenance[machine_maintenance[date_col] <= target_time]

    records = machine_maintenance.to_dict(orient='records')
    for r in records:
        if date_col in r and pd.notnull(r[date_col]):
            r[date_col] = str(r[date_col])
    return records


def get_machine_production_history(machine_id: str, timestamp: str = None, limit: int = 10) -> List[Dict]:
    """
    Returns recent production logs for machine_id up to `timestamp` if specified.
    """
    production_df = get_production_df()
    machine_production = production_df[production_df['machine_id'] == machine_id]
    if machine_production.empty:
        return []

    time_col = 'timestamp' if 'timestamp' in machine_production.columns else 'date'
    machine_production = machine_production.sort_values(time_col)

    if timestamp:
        target_time = pd.to_datetime(timestamp)
        machine_production = machine_production[machine_production[time_col] <= target_time]

    records = machine_production.tail(limit).to_dict(orient='records')
    for r in records:
        if time_col in r and pd.notnull(r[time_col]):
            r[time_col] = str(r[time_col])
    return records
