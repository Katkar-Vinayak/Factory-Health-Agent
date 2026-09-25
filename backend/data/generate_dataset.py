import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Constants
NUM_MACHINES = 10
HOURS_PER_MACHINE = 1000  # 1,000 hourly records per machine
START_DATE = datetime(2023, 1, 1)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(DATA_DIR, exist_ok=True)

METADATA_PATH = os.path.join(DATA_DIR, 'machine_metadata.csv')
SENSOR_PATH = os.path.join(DATA_DIR, 'sensor_data.csv')
MAINTENANCE_PATH = os.path.join(DATA_DIR, 'maintenance_records.csv')
PRODUCTION_PATH = os.path.join(DATA_DIR, 'production_logs.csv')

FAILURE_TYPES = [
    'Bearing Degradation',
    'Motor Overheating',
    'Cooling System Failure',
    'Hydraulic Pressure Failure',
    'Electrical Anomaly'
]


def generate_all_datasets(data_dir=DATA_DIR, force_regenerate_metadata=False):
    """
    Generate or synchronize sensor_data.csv, production_logs.csv, and maintenance_records.csv
    based on the authoritative catalog machine_metadata.csv.
    
    If machine_metadata.csv contains new machines (e.g. M_011, M_012),
    all datasets are automatically populated and kept synchronized.
    """
    np.random.seed(42)

    # 1. Authoritative Machine Metadata Handling
    machine_types = ['CNC Lathe', 'Milling Machine', 'Industrial Press', 'Welding Robot', 'Packaging Line']
    default_machines = []
    for i in range(1, NUM_MACHINES + 1):
        m_type = np.random.choice(machine_types)
        default_machines.append({
            'machine_id': f'M_{i:03d}',
            'machine_name': f'{m_type} {i}',
            'machine_type': m_type,
            'machine_age_years': np.round(np.random.uniform(1, 15), 1),
            'rated_power_kw': int(np.random.choice([50, 75, 100, 150, 200])),
            'installation_date': (START_DATE - timedelta(days=int(np.random.randint(365, 5000)))).strftime('%Y-%m-%d'),
            'operating_hours': int(np.random.randint(1000, 20000)),
            'maintenance_count': int(np.random.randint(5, 50)),
            'criticality_level': np.random.choice(['Low', 'Medium', 'High'])
        })

    metadata_file = os.path.join(data_dir, 'machine_metadata.csv')
    if os.path.exists(metadata_file) and not force_regenerate_metadata:
        df_machines = pd.read_csv(metadata_file, keep_default_na=False)
        for col in df_machines.select_dtypes(include='object').columns:
            df_machines[col] = df_machines[col].astype(str).str.strip()
    else:
        df_machines = pd.DataFrame(default_machines)
        df_machines.to_csv(metadata_file, index=False)

    base_machine_ids = {f'M_{i:03d}' for i in range(1, 11)}

    # 2. Generate Sensor Data, Maintenance Records, Production Logs
    sensor_records = []
    maintenance_records = []
    production_records = []
    maintenance_id_counter = 1

    for _, machine in df_machines.iterrows():
        m_id = str(machine['machine_id']).strip()
        is_base = m_id in base_machine_ids

        if is_base:
            base_temp = np.random.uniform(40, 50)
            base_vib = np.random.uniform(1, 3)
            base_press = np.random.uniform(110, 130)
            base_energy = np.random.uniform(60, 80)
            
            op_hours_val = machine.get('operating_hours', 10000)
            try:
                current_op_hours = int(op_hours_val)
            except (ValueError, TypeError):
                current_op_hours = 10000

            num_failures = np.random.randint(1, 4)
            failure_indices = np.sort(np.random.choice(range(100, HOURS_PER_MACHINE - 50), num_failures, replace=False))
            failure_events = {}
            for idx in failure_indices:
                failure_events[idx] = {
                    'type': np.random.choice(FAILURE_TYPES),
                    'length': np.random.randint(5, 21)
                }
        else:
            # Newly added machine (e.g. M_011, M_012):
            # Realistic healthy operating baseline
            base_temp = np.random.uniform(42.0, 46.0)
            base_vib = np.random.uniform(1.4, 1.9)
            base_press = np.random.uniform(116.0, 124.0)
            base_energy = np.random.uniform(65.0, 72.0)
            
            op_hours_val = machine.get('operating_hours', 8000)
            try:
                current_op_hours = int(op_hours_val)
            except (ValueError, TypeError):
                current_op_hours = 8000
                
            failure_events = {}

        current_time = START_DATE
        in_degradation = False
        degradation_type = None
        steps_to_failure = 0
        degradation_length = 0

        for i in range(HOURS_PER_MACHINE):
            if is_base:
                temp = base_temp + np.random.normal(0, 2)
                vib = base_vib + np.random.normal(0, 0.2)
                press = base_press + np.random.normal(0, 3)
                humid = 40 + np.random.normal(0, 5)
                energy = base_energy + np.random.normal(0, 2)
                load = 80 + np.random.normal(0, 5)
                prod_out = int(110 + np.random.normal(0, 10))
                amb_temp = 25 + np.random.normal(0, 3) + 5 * np.sin(2 * np.pi * i / 24)
            else:
                temp = base_temp + np.random.normal(0, 1.2)
                vib = base_vib + np.random.normal(0, 0.12)
                press = base_press + np.random.normal(0, 2.0)
                humid = 40 + np.random.normal(0, 3.5)
                energy = base_energy + np.random.normal(0, 1.5)
                load = 80 + np.random.normal(0, 3.5)
                prod_out = int(112 + np.random.normal(0, 7))
                amb_temp = 25 + np.random.normal(0, 3) + 5 * np.sin(2 * np.pi * i / 24)

            anomaly = 0
            failure_within_24h = 0
            f_type = "None"

            # Check if entering degradation phase
            for f_idx, f_data in failure_events.items():
                if not in_degradation and (f_idx - f_data['length']) <= i < f_idx:
                    in_degradation = True
                    degradation_type = f_data['type']
                    degradation_length = f_data['length']
                    steps_to_failure = f_idx - i
                    break

            if in_degradation:
                progress = 1.0 - (steps_to_failure / degradation_length)
                anomaly = 1
                if steps_to_failure <= 24:
                    failure_within_24h = 1

                if degradation_type == 'Bearing Degradation':
                    vib += progress * 10
                    temp += progress * 15
                    energy += progress * 20
                    prod_out -= int(progress * 30)
                elif degradation_type == 'Motor Overheating':
                    temp += progress * 30
                    energy += progress * 30
                    vib += progress * 2
                elif degradation_type == 'Cooling System Failure':
                    temp += progress * 40
                    energy += progress * 15
                elif degradation_type == 'Hydraulic Pressure Failure':
                    press -= progress * 50
                    prod_out -= int(progress * 40)
                    vib += progress * 3
                elif degradation_type == 'Electrical Anomaly':
                    energy += progress * 40 + np.random.normal(0, 10)
                    prod_out -= int(progress * 20)
                    temp += progress * 5

                steps_to_failure -= 1
                if steps_to_failure <= 0:
                    f_type = degradation_type
                    in_degradation = False

                    component_map = {
                        'Bearing Degradation': 'Bearing',
                        'Motor Overheating': 'Motor',
                        'Cooling System Failure': 'Cooling System',
                        'Hydraulic Pressure Failure': 'Hydraulic Pump',
                        'Electrical Anomaly': 'Electrical System'
                    }
                    maintenance_records.append({
                        'maintenance_id': f'MAINT_{maintenance_id_counter:04d}',
                        'machine_id': m_id,
                        'maintenance_date': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'maintenance_type': 'Corrective',
                        'component': component_map[degradation_type],
                        'description': f'Fix {degradation_type}',
                        'downtime_hours': int(np.random.randint(4, 48)),
                        'maintenance_cost': float(np.round(np.random.uniform(500, 5000), 2)),
                        'technician_notes': f'Replaced {component_map[degradation_type]} after failure.'
                    })
                    maintenance_id_counter += 1

            # End-of-series degradation for realistic mixed factory health state at latest record (hour 999)
            # Fleet Target (24 machines): Healthy = 15 (62.5%), Warning = 7 (29.2%), Critical = 2 (8.3%)
            # 1. Critical Machines (2):
            #    - M_003: Active Bearing Degradation (Preserved primary demo scenario)
            #    - M_010: Active Motor Overheating (Secondary critical scenario with distinct failure signature)
            # 2. Warning Machines (7):
            #    - Early Bearing / Mechanical Drift: M_005, M_012, M_015
            #    - Early Thermal / Cooling Drift: M_007, M_018
            #    - Early Electrical / Hydraulic Drift: M_013, M_020
            # 3. Healthy Machines (15):
            #    - M_001, M_002, M_004, M_006, M_008, M_009, M_011, M_014, M_016, M_017, M_019, M_021, M_022, M_023, M_024
            
            # --- CRITICAL PROFILES ---
            if m_id == 'M_003' and i >= 980:
                # Active Bearing Degradation culminating near hour 1000 (Critical pre-failure state)
                progress = (i - 980 + 1) / 20.0
                vib += progress * 9.5
                temp += progress * 14.5
                energy += progress * 18.0
                prod_out = max(0, prod_out - int(progress * 28))
                anomaly = 1
                failure_within_24h = 1
            elif m_id == 'M_010' and i >= 980:
                # Active Motor Overheating culminating near hour 1000 (Critical pre-failure state)
                progress = (i - 980 + 1) / 20.0
                temp += progress * 34.0
                energy += progress * 24.0
                vib += progress * 1.8
                prod_out = max(0, prod_out - int(progress * 16))
                anomaly = 1
                failure_within_24h = 1
                
            # --- WARNING PROFILES (Early-stage deterioration, non-critical, anomaly=0, failure_within_24h=0) ---
            # Profile A: Early Bearing / Mechanical Degradation (M_005, M_012, M_015)
            elif m_id == 'M_005' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                vib += progress * 1.45
                temp += progress * 4.5
                energy += progress * 17.5
                prod_out = max(0, prod_out - int(progress * 12))
            elif m_id == 'M_012' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                vib += progress * 1.22
                temp += progress * 4.2
                energy += progress * 8.5
                prod_out = max(0, prod_out - int(progress * 8))
            elif m_id == 'M_015' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                vib += progress * 1.5
                temp += progress * 4.5
                energy += progress * 11.0
                prod_out = max(0, prod_out - int(progress * 10))
                
            # Profile B: Early Thermal / Cooling Degradation (M_007, M_018)
            elif m_id == 'M_007' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                temp += progress * 4.5
                energy += progress * 4.0
                vib += progress * 0.05
                prod_out = max(0, prod_out - int(progress * 10))
            elif m_id == 'M_018' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                temp += progress * 13.5
                energy += progress * 12.0
                vib += progress * 0.3
                prod_out = max(0, prod_out - int(progress * 8))
                
            # Profile C: Early Energy / Electrical or Hydraulic Drift (M_013, M_020)
            elif m_id == 'M_013' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                energy += progress * 18.5
                press -= progress * 12.0
                temp += progress * 3.5
                prod_out = max(0, prod_out - int(progress * 10))
            elif m_id == 'M_020' and i >= 975:
                progress = (i - 975 + 1) / 25.0
                energy += progress * 16.5
                press -= progress * 12.0
                temp += progress * 3.5
                prod_out = max(0, prod_out - int(progress * 10))

            # Bound values to realistic physical ranges
            temp = max(10, min(150, temp))
            vib = max(0.1, min(50, vib))
            press = max(10, min(200, press))
            humid = max(10, min(90, humid))
            energy = max(10, min(300, energy))
            load = max(0, min(100, load))
            prod_out = max(0, prod_out)

            sensor_records.append({
                'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'machine_id': m_id,
                'temperature_c': round(temp, 2),
                'vibration_mm_s': round(vib, 2),
                'pressure_bar': round(press, 2),
                'humidity_percent': round(humid, 2),
                'energy_consumption_kwh': round(energy, 2),
                'load_percent': round(load, 2),
                'production_output_units': prod_out,
                'operating_hours': current_op_hours,
                'ambient_temperature_c': round(amb_temp, 2),
                'anomaly': anomaly,
                'failure_within_24h': failure_within_24h,
                'failure_type': f_type
            })

            # Production Log
            target = 120
            rej = max(0, int(np.random.normal(2, 1)) + (5 if anomaly else 0))
            dt_mins = 0
            if f_type != "None":
                dt_mins = int(np.random.randint(60, 240))
                prod_out = max(0, prod_out - (dt_mins // 2))

            eff = min(100.0, (prod_out / target) * 100) if target > 0 else 0

            production_records.append({
                'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'machine_id': m_id,
                'production_target': target,
                'production_output': prod_out,
                'rejected_units': rej,
                'downtime_minutes': dt_mins,
                'efficiency_percent': round(eff, 2)
            })

            current_time += timedelta(hours=1)
            current_op_hours += 1

    # 3. Preventive Maintenance History for all machines
    for m in df_machines['machine_id']:
        for _ in range(np.random.randint(1, 4)):
            dt = START_DATE + timedelta(days=int(np.random.randint(5, 40)))
            maintenance_records.append({
                'maintenance_id': f'MAINT_{maintenance_id_counter:04d}',
                'machine_id': m,
                'maintenance_date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'maintenance_type': 'Preventive',
                'component': np.random.choice(['Filter', 'Lubrication', 'Sensor Calibration']),
                'description': 'Routine check',
                'downtime_hours': int(np.random.randint(1, 4)),
                'maintenance_cost': float(np.round(np.random.uniform(100, 500), 2)),
                'technician_notes': 'All systems normal.'
            })
            maintenance_id_counter += 1

    df_sensor = pd.DataFrame(sensor_records)
    df_maint = pd.DataFrame(maintenance_records)
    df_prod = pd.DataFrame(production_records)

    # 4. Save Synchronized Datasets
    sensor_file = os.path.join(data_dir, 'sensor_data.csv')
    maint_file = os.path.join(data_dir, 'maintenance_records.csv')
    prod_file = os.path.join(data_dir, 'production_logs.csv')

    df_sensor.to_csv(sensor_file, index=False)
    df_maint.to_csv(maint_file, index=False)
    df_prod.to_csv(prod_file, index=False)

    # 5. Automated Synchronization Validation
    metadata_machines = set(df_machines['machine_id'].unique())
    sensor_machines = set(df_sensor['machine_id'].unique())
    prod_machines = set(df_prod['machine_id'].unique())

    missing_in_sensor = metadata_machines - sensor_machines
    missing_in_prod = metadata_machines - prod_machines

    if missing_in_sensor or missing_in_prod:
        error_msg = "SYNCHRONIZATION ERROR: Incomplete dataset generation!\n"
        if missing_in_sensor:
            error_msg += f"- Missing in sensor_data.csv: {sorted(list(missing_in_sensor))}\n"
        if missing_in_prod:
            error_msg += f"- Missing in production_logs.csv: {sorted(list(missing_in_prod))}\n"
        raise RuntimeError(error_msg)

    print("=" * 60)
    print("DATA SYNCHRONIZATION AND GENERATION COMPLETE")
    print("=" * 60)
    print(f"Authoritative catalog: {metadata_file} ({len(df_machines)} machines)")
    print(f"- sensor_data.csv: {len(df_sensor)} records")
    print(f"- production_logs.csv: {len(df_prod)} records")
    print(f"- maintenance_records.csv: {len(df_maint)} records")
    print(f"Synchronization check passed: All {len(metadata_machines)} machines synchronized.")
    print("=" * 60)

    return df_machines, df_sensor, df_maint, df_prod


if __name__ == '__main__':
    df_machines, df_sensor, df_maint, df_prod = generate_all_datasets()
