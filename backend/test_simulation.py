"""
Automated Test Suite for What-If 24-Hour Impact Simulator
Verifies:
1. M_003 preset at 2023-01-19 22:00:00 (HIGH risk, Bearing Degradation)
2. M_010 latest critical scenario (HIGH risk, Motor Overheating)
3. M_005 warning scenario (MEDIUM risk, early degradation)
4. M_001 healthy scenario (LOW risk)
5. HTTP 404 for invalid machine ID
6. HTTP 422 for missing required fields
7. Simulation trajectories, output structures, and avoided exposure calculations
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def run_simulation_tests():
    print("=" * 60)
    print("RUNNING WHAT-IF 24-HOUR IMPACT SIMULATOR TEST SUITE")
    print("=" * 60)

    # Initialize authenticated session
    session = requests.Session()
    login_resp = session.post(f"{BASE_URL}/auth/login", json={
        "email": "operator@factory.com",
        "password": "Factory@123!"
    })
    assert login_resp.status_code == 200, f"Auth failed: {login_resp.text}"

    # -------------------------------------------------------------
    # TEST 1: M_003 Demonstration Preset
    # -------------------------------------------------------------
    print("\n--- TEST 1: Machine M_003 Demo Preset (2023-01-19 22:00:00) ---")
    payload_m003 = {
        "machine_id": "M_003",
        "timestamp": "2023-01-19 22:00:00"
    }
    resp = session.post(f"{BASE_URL}/simulation/what-if", json=payload_m003)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data_003 = resp.json()

    print(f"Machine ID:                    {data_003['machine_id']}")
    print(f"Timestamp:                     {data_003['timestamp']}")
    print(f"Diagnosed Root Cause:          {data_003['root_cause']}")
    print(f"Current Risk Level:            {data_003['current_state']['risk_level']}")
    print(f"Current Failure Probability:   {data_003['current_state']['failure_probability']}")
    print(f"Current Anomaly:               {data_003['current_state']['anomaly']}")
    print(f"Current Downtime Risk:         {data_003['current_state']['downtime_risk']}")

    assert data_003["root_cause"] == "Bearing Degradation", f"Expected Bearing Degradation, got {data_003['root_cause']}"
    assert data_003["current_state"]["risk_level"] == "HIGH", f"Expected HIGH risk, got {data_003['current_state']['risk_level']}"
    assert data_003["current_state"]["anomaly"] is True, "Expected anomaly to be True"
    assert len(data_003["intervene_now"]["trajectory"]) == 24, "Intervene trajectory must have 24 hourly points"
    assert len(data_003["do_nothing"]["trajectory"]) == 24, "Do Nothing trajectory must have 24 hourly points"

    int_risk_24 = data_003["intervene_now"]["projected_risk_index"]
    dn_risk_24 = data_003["do_nothing"]["projected_risk_index"]
    prod_avoided = data_003["estimated_difference"]["production_loss_avoided"]
    energy_avoided = data_003["estimated_difference"]["energy_wastage_avoided"]
    dt_avoided = data_003["estimated_difference"]["downtime_exposure_avoided"]

    print(f"Intervene Now Risk Index (24h): {int_risk_24} / 100")
    print(f"Do Nothing Risk Index (24h):    {dn_risk_24} / 100")
    print(f"Production Loss Avoided:        {prod_avoided} units")
    print(f"Energy Wastage Avoided:         {energy_avoided} kWh")
    print(f"Downtime Exposure Avoided:      {dt_avoided} hours")

    assert int_risk_24 < dn_risk_24, "Intervene risk must be significantly lower than Do Nothing"
    assert prod_avoided >= 0, "Production loss avoided must be non-negative"
    assert energy_avoided >= 0, "Energy wastage avoided must be non-negative"
    assert dt_avoided > 0, "Downtime exposure avoided must be positive"
    print(">> TEST 1 PASSED!")

    # -------------------------------------------------------------
    # TEST 2: M_010 Second Critical Machine (Motor Overheating)
    # -------------------------------------------------------------
    print("\n--- TEST 2: Machine M_010 (Latest Critical Scenario) ---")
    payload_m010 = {"machine_id": "M_010"}
    resp = session.post(f"{BASE_URL}/simulation/what-if", json=payload_m010)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data_010 = resp.json()

    print(f"Machine ID:                    {data_010['machine_id']}")
    print(f"Diagnosed Root Cause:          {data_010['root_cause']}")
    print(f"Current Risk Level:            {data_010['current_state']['risk_level']}")
    print(f"Intervention Action:           {data_010['assumptions']['intervention_action']}")
    print(f"Intervene Now Risk Index (24h): {data_010['intervene_now']['projected_risk_index']}")
    print(f"Do Nothing Risk Index (24h):    {data_010['do_nothing']['projected_risk_index']}")
    print(f"Energy Wastage Avoided:         {data_010['estimated_difference']['energy_wastage_avoided']} kWh")

    assert data_010["root_cause"] == "Motor Overheating", f"Expected Motor Overheating, got {data_010['root_cause']}"
    assert data_010["current_state"]["risk_level"] == "HIGH", f"Expected HIGH risk, got {data_010['current_state']['risk_level']}"
    assert data_010["assumptions"]["root_cause_profile"] != data_003["assumptions"]["root_cause_profile"], "M_010 must have a different profile from M_003"
    print(">> TEST 2 PASSED!")

    # -------------------------------------------------------------
    # TEST 3: M_005 Warning Machine (MEDIUM Risk)
    # -------------------------------------------------------------
    print("\n--- TEST 3: Machine M_005 (Warning Scenario / MEDIUM Risk) ---")
    payload_m005 = {"machine_id": "M_005"}
    resp = session.post(f"{BASE_URL}/simulation/what-if", json=payload_m005)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data_005 = resp.json()

    print(f"Machine ID:                    {data_005['machine_id']}")
    print(f"Current Risk Level:            {data_005['current_state']['risk_level']}")
    print(f"Current Failure Probability:   {data_005['current_state']['failure_probability']}")
    print(f"Intervene Now Risk Index (24h): {data_005['intervene_now']['projected_risk_index']}")
    print(f"Do Nothing Risk Index (24h):    {data_005['do_nothing']['projected_risk_index']}")

    assert data_005["current_state"]["risk_level"] == "MEDIUM", f"Expected MEDIUM risk, got {data_005['current_state']['risk_level']}"
    assert 0.30 <= data_005["current_state"]["failure_probability"] <= 0.50, "Failure prob must be in warning range"
    print(">> TEST 3 PASSED!")

    # -------------------------------------------------------------
    # TEST 4: M_001 Healthy Machine (LOW Risk)
    # -------------------------------------------------------------
    print("\n--- TEST 4: Machine M_001 (Healthy Machine / LOW Risk) ---")
    payload_m001 = {"machine_id": "M_001"}
    resp = session.post(f"{BASE_URL}/simulation/what-if", json=payload_m001)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data_001 = resp.json()

    print(f"Machine ID:                    {data_001['machine_id']}")
    print(f"Current Risk Level:            {data_001['current_state']['risk_level']}")
    print(f"Current Failure Probability:   {data_001['current_state']['failure_probability']}")

    assert data_001["current_state"]["risk_level"] == "LOW", f"Expected LOW risk, got {data_001['current_state']['risk_level']}"
    print(">> TEST 4 PASSED!")

    # -------------------------------------------------------------
    # TEST 5: HTTP 404 for Unknown Machine
    # -------------------------------------------------------------
    print("\n--- TEST 5: Invalid Machine ID (HTTP 404) ---")
    resp_404 = session.post(f"{BASE_URL}/simulation/what-if", json={"machine_id": "M_999"})
    print(f"Status Code: {resp_404.status_code}, Detail: {resp_404.text}")
    assert resp_404.status_code == 404, f"Expected 404, got {resp_404.status_code}"
    print(">> TEST 5 PASSED!")

    # -------------------------------------------------------------
    # TEST 6: HTTP 422 for Malformed Input
    # -------------------------------------------------------------
    print("\n--- TEST 6: Missing machine_id (HTTP 422) ---")
    resp_422 = session.post(f"{BASE_URL}/simulation/what-if", json={})
    print(f"Status Code: {resp_422.status_code}, Detail: {resp_422.text}")
    assert resp_422.status_code == 422, f"Expected 422, got {resp_422.status_code}"
    print(">> TEST 6 PASSED!")

    print("\n" + "=" * 60)
    print("ALL WHAT-IF SIMULATOR TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation_tests()
