import os
import time
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000/api/machines"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
METADATA_PATH = os.path.join(DATA_DIR, "machine_metadata.csv")
SENSORS_PATH = os.path.join(DATA_DIR, "sensor_data.csv")

def simulate_frontend_dashboard():
    """
    Exactly mirrors the logic executed by frontend/app/page.tsx:
    1. getMachines()
    2. for each machine, getMachineAnalysis(m.machine_id)
    3. compute risk_level:
       - if anomaly or prob > 0.5 => HIGH
       - elif prob > 0.3 => MEDIUM
       - else => LOW
       - if error (e.g. 404 No sensor data) => UNKNOWN
    4. compute totalCount, healthyCount, warningCount, criticalCount, highCriticalityCount
    """
    res = requests.get(f"{API_URL}/", headers={"Cache-Control": "no-cache"})
    if res.status_code != 200:
        raise RuntimeError(f"Failed to fetch machines: {res.status_code} {res.text}")
    raw_machines = res.json()

    enriched = []
    for m in raw_machines:
        mid = m["machine_id"]
        try:
            a_res = requests.get(f"{API_URL}/{mid}/analysis", headers={"Cache-Control": "no-cache"})
            if a_res.status_code == 200:
                data = a_res.json()
                prob = data["analysis"]["failure_probability"]
                anom = data["analysis"]["anomaly"]
                if anom or prob > 0.5:
                    risk = "HIGH"
                elif prob > 0.3:
                    risk = "MEDIUM"
                else:
                    risk = "LOW"
                enriched.append({"metadata": m, "risk_level": risk, "sensors": data.get("sensors")})
            else:
                enriched.append({"metadata": m, "risk_level": "UNKNOWN", "sensors": None})
        except Exception:
            enriched.append({"metadata": m, "risk_level": "UNKNOWN", "sensors": None})

    total_count = len(enriched)
    healthy_count = sum(1 for m in enriched if m["risk_level"] == "LOW")
    warning_count = sum(1 for m in enriched if m["risk_level"] == "MEDIUM")
    critical_count = sum(1 for m in enriched if m["risk_level"] == "HIGH")
    unknown_count = sum(1 for m in enriched if m["risk_level"] == "UNKNOWN")
    high_crit_count = sum(
        1 for m in enriched if str(m["metadata"].get("criticality_level", "")).strip().lower() == "high"
    )

    return {
        "machines": enriched,
        "total": total_count,
        "healthy": healthy_count,
        "warning": warning_count,
        "critical": critical_count,
        "unknown": unknown_count,
        "high_criticality": high_crit_count
    }

def run_tests():
    print("==================================================")
    print("RUNNING DYNAMIC MACHINE & HEALTH COUNTS TEST SUITE")
    print("==================================================")

    # Backup original files to ensure safety
    meta_df_orig = pd.read_csv(METADATA_PATH)
    sensors_df_orig = pd.read_csv(SENSORS_PATH)

    try:
        # TEST 1: Baseline catalog
        print("\n--- TEST 1: Current Machine Catalog ---")
        t1 = simulate_frontend_dashboard()
        print(f"Total Machines:           {t1['total']}")
        print(f"Healthy:                  {t1['healthy']}")
        print(f"Warning:                  {t1['warning']}")
        print(f"Critical:                 {t1['critical']}")
        print(f"High Criticality Assets:  {t1['high_criticality']}")
        print(f"Unknown (Awaiting Tel.):  {t1['unknown']}")
        assert t1['total'] == 24, f"Expected 24 total machines, got {t1['total']}"
        assert t1['healthy'] == 15, f"Expected 15 healthy, got {t1['healthy']}"
        assert t1['warning'] == 7, f"Expected 7 warning, got {t1['warning']}"
        assert t1['critical'] == 2, f"Expected 2 critical, got {t1['critical']}"
        assert t1['high_criticality'] == 9, f"Expected 9 high criticality, got {t1['high_criticality']}"
        assert t1['unknown'] == 0, f"Expected 0 unknown, got {t1['unknown']}"
        print(">> TEST 1 PASSED!")

        # TEST 2: Add a new machine with criticality_level = HIGH, no sensor telemetry
        print("\n--- TEST 2: Add Machine with High Criticality & No Telemetry ---")
        new_machine_id = "M_099"
        new_row = {
            "machine_id": new_machine_id,
            "machine_name": "Turbine Generator 99",
            "machine_type": "Turbine Generator",
            "machine_age_years": 3.5,
            "rated_power_kw": 500,
            "installation_date": "2020-05-15",
            "operating_hours": 14200,
            "maintenance_count": 15,
            "criticality_level": "High"
        }
        meta_df = pd.read_csv(METADATA_PATH)
        meta_df = pd.concat([meta_df, pd.DataFrame([new_row])], ignore_index=True)
        meta_df.to_csv(METADATA_PATH, index=False)
        time.sleep(0.5)

        t2 = simulate_frontend_dashboard()
        print(f"Total Machines:           {t2['total']} (Change: {t2['total'] - t1['total']})")
        print(f"Healthy:                  {t2['healthy']} (Change: {t2['healthy'] - t1['healthy']})")
        print(f"Warning:                  {t2['warning']} (Change: {t2['warning'] - t1['warning']})")
        print(f"Critical:                 {t2['critical']} (Change: {t2['critical'] - t1['critical']})")
        print(f"High Criticality Assets:  {t2['high_criticality']} (Change: {t2['high_criticality'] - t1['high_criticality']})")
        print(f"Unknown (Awaiting Tel.):  {t2['unknown']} (Change: {t2['unknown'] - t1['unknown']})")
        
        new_m = next((m for m in t2["machines"] if m["metadata"]["machine_id"] == new_machine_id), None)
        assert new_m is not None, "New machine not found in API response!"
        assert new_m["risk_level"] == "UNKNOWN", f"Expected UNKNOWN risk, got {new_m['risk_level']}"
        assert t2['total'] == t1['total'] + 1, "Total did not increase by 1!"
        assert t2['high_criticality'] == t1['high_criticality'] + 1, "High criticality did not increase by 1!"
        assert t2['healthy'] == t1['healthy'], "Healthy count changed unexpectedly!"
        assert t2['warning'] == t1['warning'], "Warning count changed unexpectedly!"
        assert t2['critical'] == t1['critical'], "Critical count changed unexpectedly!"
        assert t2['unknown'] == 1, "Unknown count should be 1 (Awaiting Telemetry)!"
        print(">> TEST 2 PASSED!")

        # TEST 3: Add sensor telemetry for that machine producing risk_level = MEDIUM
        print("\n--- TEST 3: Add Telemetry Producing MEDIUM Risk ---")
        med_telemetry = {
            "timestamp": "2023-01-15 12:00:00",
            "machine_id": new_machine_id,
            "temperature_c": 52.0,
            "vibration_mm_s": 2.82,
            "pressure_bar": 117.44,
            "humidity_percent": 35.93,
            "energy_consumption_kwh": 80.0,
            "load_percent": 81.33,
            "production_output_units": 107,
            "operating_hours": 12284,
            "ambient_temperature_c": 25.42,
            "anomaly": 0,
            "failure_within_24h": 0,
            "failure_type": None
        }
        sensors_df = pd.read_csv(SENSORS_PATH)
        sensors_df = pd.concat([sensors_df, pd.DataFrame([med_telemetry])], ignore_index=True)
        sensors_df.to_csv(SENSORS_PATH, index=False)
        time.sleep(0.5)

        t3 = simulate_frontend_dashboard()
        print(f"Total Machines:           {t3['total']} (Change vs T2: {t3['total'] - t2['total']})")
        print(f"Healthy:                  {t3['healthy']} (Change vs T2: {t3['healthy'] - t2['healthy']})")
        print(f"Warning:                  {t3['warning']} (Change vs T2: {t3['warning'] - t2['warning']})")
        print(f"Critical:                 {t3['critical']} (Change vs T2: {t3['critical'] - t2['critical']})")
        print(f"High Criticality Assets:  {t3['high_criticality']} (Change vs T2: {t3['high_criticality'] - t2['high_criticality']})")
        print(f"Unknown (Awaiting Tel.):  {t3['unknown']} (Change vs T2: {t3['unknown'] - t2['unknown']})")

        new_m = next((m for m in t3["machines"] if m["metadata"]["machine_id"] == new_machine_id), None)
        assert new_m["risk_level"] == "MEDIUM", f"Expected MEDIUM risk, got {new_m['risk_level']}"
        assert t3['total'] == t2['total'], "Total changed unexpectedly!"
        assert t3['high_criticality'] == t2['high_criticality'], "High criticality changed unexpectedly!"
        assert t3['healthy'] == t2['healthy'], "Healthy count changed unexpectedly!"
        assert t3['warning'] == t2['warning'] + 1, "Warning count did not increase by 1!"
        assert t3['critical'] == t2['critical'], "Critical count changed unexpectedly!"
        assert t3['unknown'] == 0, "Unknown count should have decreased to 0!"
        print(">> TEST 3 PASSED!")

        # TEST 4: Change machine's current telemetry/risk to HIGH
        print("\n--- TEST 4: Update Telemetry to Produce HIGH Risk ---")
        high_telemetry = {
            "timestamp": "2023-01-15 13:00:00",
            "machine_id": new_machine_id,
            "temperature_c": 50.58,
            "vibration_mm_s": 2.23,
            "pressure_bar": 113.59,
            "humidity_percent": 34.22,
            "energy_consumption_kwh": 67.14,
            "load_percent": 85.64,
            "production_output_units": 111,
            "operating_hours": 12545,
            "ambient_temperature_c": 17.16,
            "anomaly": 1,
            "failure_within_24h": 1,
            "failure_type": "Bearing Wear"
        }
        sensors_df = pd.read_csv(SENSORS_PATH)
        sensors_df = pd.concat([sensors_df, pd.DataFrame([high_telemetry])], ignore_index=True)
        sensors_df.to_csv(SENSORS_PATH, index=False)
        time.sleep(0.5)

        t4 = simulate_frontend_dashboard()
        print(f"Total Machines:           {t4['total']} (Change vs T3: {t4['total'] - t3['total']})")
        print(f"Healthy:                  {t4['healthy']} (Change vs T3: {t4['healthy'] - t3['healthy']})")
        print(f"Warning:                  {t4['warning']} (Change vs T3: {t4['warning'] - t3['warning']})")
        print(f"Critical:                 {t4['critical']} (Change vs T3: {t4['critical'] - t3['critical']})")
        print(f"High Criticality Assets:  {t4['high_criticality']} (Change vs T3: {t4['high_criticality'] - t3['high_criticality']})")
        print(f"Unknown (Awaiting Tel.):  {t4['unknown']} (Change vs T3: {t4['unknown'] - t3['unknown']})")

        new_m = next((m for m in t4["machines"] if m["metadata"]["machine_id"] == new_machine_id), None)
        assert new_m["risk_level"] == "HIGH", f"Expected HIGH risk, got {new_m['risk_level']}"
        assert t4['total'] == t3['total'], "Total changed unexpectedly!"
        assert t4['high_criticality'] == t3['high_criticality'], "High criticality changed unexpectedly!"
        assert t4['warning'] == t3['warning'] - 1, "Warning did not decrease by 1!"
        assert t4['critical'] == t3['critical'] + 1, "Critical did not increase by 1!"
        assert t4['healthy'] == t3['healthy'], "Healthy count changed unexpectedly!"
        print(">> TEST 4 PASSED!")

        # TEST 5: Remove the machine from backend metadata
        print("\n--- TEST 5: Remove Machine from Backend Metadata ---")
        meta_df = pd.read_csv(METADATA_PATH)
        meta_df = meta_df[meta_df["machine_id"] != new_machine_id]
        meta_df.to_csv(METADATA_PATH, index=False)
        time.sleep(0.5)

        t5 = simulate_frontend_dashboard()
        print(f"Total Machines:           {t5['total']} (Change vs T4: {t5['total'] - t4['total']})")
        print(f"Healthy:                  {t5['healthy']} (Change vs T4: {t5['healthy'] - t4['healthy']})")
        print(f"Warning:                  {t5['warning']} (Change vs T4: {t5['warning'] - t4['warning']})")
        print(f"Critical:                 {t5['critical']} (Change vs T4: {t5['critical'] - t4['critical']})")
        print(f"High Criticality Assets:  {t5['high_criticality']} (Change vs T4: {t5['high_criticality'] - t4['high_criticality']})")
        print(f"Unknown (Awaiting Tel.):  {t5['unknown']} (Change vs T4: {t5['unknown'] - t4['unknown']})")

        assert t5['total'] == t4['total'] - 1, "Total did not decrease by 1!"
        assert t5['high_criticality'] == t4['high_criticality'] - 1, "High criticality did not decrease by 1!"
        assert t5['critical'] == t4['critical'] - 1, "Critical did not decrease by 1!"
        assert t5['warning'] == t4['warning'], "Warning changed unexpectedly!"
        assert t5['healthy'] == t4['healthy'], "Healthy changed unexpectedly!"
        print(">> TEST 5 PASSED!")

    finally:
        # Restore original CSV files
        print("\n--- Restoring original metadata and sensor CSV files ---")
        meta_df_orig.to_csv(METADATA_PATH, index=False)
        sensors_df_orig.to_csv(SENSORS_PATH, index=False)
        print("Original files restored cleanly.")

if __name__ == "__main__":
    run_tests()
