import os, sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
METADATA_PATH = os.path.join(DATA_DIR, 'machine_metadata.csv')

np.random.seed(42)
NUM_BASE_MACHINES = 10
HOURS_PER_MACHINE = 1000
START_DATE = datetime(2023, 1, 1)

machine_types = ['CNC Lathe', 'Milling Machine', 'Industrial Press', 'Welding Robot', 'Packaging Line']
machines = []
for i in range(1, NUM_BASE_MACHINES + 1):
    m_type = np.random.choice(machine_types)
    machines.append({
        'machine_id': f'M_{i:03d}',
        'machine_name': f'{m_type} {i}',
        'machine_type': m_type,
        'machine_age_years': np.round(np.random.uniform(1, 15), 1),
        'rated_power_kw': np.random.choice([50, 75, 100, 150, 200]),
        'installation_date': (START_DATE - timedelta(days=int(np.random.randint(365, 5000)))).strftime('%Y-%m-%d'),
        'operating_hours': int(np.random.randint(1000, 20000)),
        'maintenance_count': int(np.random.randint(5, 50)),
        'criticality_level': np.random.choice(['Low', 'Medium', 'High'])
    })
df_base = pd.DataFrame(machines)

df_disk = pd.read_csv(METADATA_PATH, keep_default_na=False)
for col in df_disk.select_dtypes(include='object').columns:
    df_disk[col] = df_disk[col].astype(str).str.strip()

# Combine: base machines updated with disk values, plus any new machines
df_machines = df_disk

FAILURE_TYPES = [
    'Bearing Degradation',
    'Motor Overheating',
    'Cooling System Failure',
    'Hydraulic Pressure Failure',
    'Electrical Anomaly'
]

sensor_records = []
maintenance_records = []
production_records = []
maintenance_id_counter = 1

for idx, machine in df_machines.iterrows():
    m_id = machine['machine_id']
    is_base = int(m_id.split('_')[1]) <= 10 if m_id.startswith('M_') and m_id.split('_')[1].isdigit() else False
    
    if is_base:
        base_temp = np.random.uniform(40, 50)
        base_vib = np.random.uniform(1, 3)
        base_press = np.random.uniform(110, 130)
        base_energy = np.random.uniform(60, 80)
        current_op_hours = int(machine['operating_hours']) if str(machine['operating_hours']).isdigit() else 10000
        num_failures = np.random.randint(1, 4)
        failure_indices = np.sort(np.random.choice(range(100, HOURS_PER_MACHINE - 50), num_failures, replace=False))
        failure_events = {}
        for f_idx in failure_indices:
            failure_events[f_idx] = {
                'type': np.random.choice(FAILURE_TYPES),
                'length': np.random.randint(5, 21)
            }
    else:
        # Healthy baseline for new machine
        base_temp = np.random.uniform(42, 48)
        base_vib = np.random.uniform(1.4, 2.0)
        base_press = np.random.uniform(115, 125)
        base_energy = np.random.uniform(64, 72)
        current_op_hours = int(machine['operating_hours']) if str(machine['operating_hours']).isdigit() else 10000
        failure_events = {}
        
    current_time = START_DATE
    in_degradation = False
    degradation_type = None
    steps_to_failure = 0
    degradation_length = 0
    
    for i in range(HOURS_PER_MACHINE):
        temp = base_temp + np.random.normal(0, 2)
        vib = base_vib + np.random.normal(0, 0.2)
        press = base_press + np.random.normal(0, 3)
        humid = 40 + np.random.normal(0, 5)
        energy = base_energy + np.random.normal(0, 2)
        load = 80 + np.random.normal(0, 5)
        prod_out = int(110 + np.random.normal(0, 10))
        amb_temp = 25 + np.random.normal(0, 3) + 5 * np.sin(2 * np.pi * i / 24)
        
        anomaly = 0
        failure_within_24h = 0
        f_type = 'None'
        
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
                
        # End-of-series degradation for base machines
        if m_id == 'M_003' and i >= 980:
            progress = (i - 980 + 1) / 20.0
            vib += progress * 9.5
            temp += progress * 14.5
            energy += progress * 18.0
            prod_out = max(0, prod_out - int(progress * 28))
            anomaly = 1
            failure_within_24h = 1
        elif m_id == 'M_005' and i >= 975:
            progress = (i - 975 + 1) / 25.0
            vib += progress * 1.3
            temp += progress * 6.0
            energy += progress * 17.0
            prod_out = max(0, prod_out - int(progress * 15))
        elif m_id == 'M_007' and i >= 975:
            progress = (i - 975 + 1) / 25.0
            vib += progress * 0.32
            temp += progress * 3.7
            energy += progress * 3.0
            prod_out = max(0, prod_out - int(progress * 8))
            
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
        
        target = 120
        rej = max(0, int(np.random.normal(2, 1)) + (5 if anomaly else 0))
        dt_mins = 0
        if f_type != 'None':
            dt_mins = np.random.randint(60, 240)
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

# Add preventive maintenance for all machines
for m in df_machines['machine_id']:
    for _ in range(np.random.randint(1, 4)):
        dt = START_DATE + timedelta(days=np.random.randint(5, 40))
        maintenance_records.append({
            'maintenance_id': f'MAINT_{maintenance_id_counter:04d}',
            'machine_id': m,
            'maintenance_date': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'maintenance_type': 'Preventive',
            'component': np.random.choice(['Filter', 'Lubrication', 'Sensor Calibration']),
            'description': 'Routine check',
            'downtime_hours': np.random.randint(1, 4),
            'maintenance_cost': np.round(np.random.uniform(100, 500), 2),
            'technician_notes': 'All systems normal.'
        })
        maintenance_id_counter += 1

df_sensor = pd.DataFrame(sensor_records)

# Check M_003 preset at 2023-01-19 22:00:00
m3_preset = df_sensor[(df_sensor['machine_id'] == 'M_003') & (df_sensor['timestamp'] == '2023-01-19 22:00:00')].iloc[0].to_dict()
temp_val = m3_preset['temperature_c']
vib_val = m3_preset['vibration_mm_s']
anom_val = m3_preset['anomaly']
fail_val = m3_preset['failure_within_24h']
print(f"M_003 preset at 2023-01-19 22:00:00: temp={temp_val}, vib={vib_val}, anom={anom_val}, fail={fail_val}")

# Retrain models
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml'))
from feature_engineering import create_features, ALL_FEATURES
from sklearn.ensemble import IsolationForest, RandomForestClassifier

df_feat = create_features(df_sensor)
iso = IsolationForest(contamination=0.027, random_state=42, n_estimators=100)
iso.fit(df_feat[ALL_FEATURES])

df_feat_sorted = df_feat.sort_values('timestamp').reset_index(drop=True)
split_idx = int(len(df_feat_sorted) * 0.8)
train_df = df_feat_sorted.iloc[:split_idx]
rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
rf.fit(train_df[ALL_FEATURES], train_df['failure_within_24h'])

print('\nLatest predictions across all machines:')
counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
for mid in sorted(df_sensor['machine_id'].unique()):
    rec = df_sensor[df_sensor['machine_id'] == mid].iloc[-1].to_dict()
    df_rec = create_features(pd.DataFrame([rec]))
    anom = bool(iso.predict(df_rec[ALL_FEATURES])[0] == -1)
    prob = float(rf.predict_proba(df_rec[ALL_FEATURES])[0][1])
    risk = 'HIGH' if anom or prob > 0.5 else ('MEDIUM' if prob > 0.3 else 'LOW')
    counts[risk] += 1
    print(f"{mid:7s} | {risk:10s} | prob={prob:.3f} | anom={str(anom):5s}")

print('\nSummary Counts:', counts)
