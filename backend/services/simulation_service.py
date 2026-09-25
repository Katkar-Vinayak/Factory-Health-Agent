"""
What-If 24-Hour Impact Simulation Service
Decision-support simulation service comparing two operational paths over a 24-hour horizon:
  - Scenario A: Intervene Now (apply recommended load de-rating, lubrication, cooling or electrical checks)
  - Scenario B: Do Nothing / Continue Current Operation (unmitigated trend progression)

All projected outputs are scenario estimates for operational decision support,
derived deterministically from current ML risk states, recent sensor trends, and configured intervention assumptions.
"""

import math
from typing import Dict, Any, List, Optional
import numpy as np

from services import machine_service
from services import ml_service
from agents.rca_agent import run_deterministic_rca

# ---------------------------------------------------------------------------
# Documented Intervention Assumptions & Profiles
# ---------------------------------------------------------------------------
INTERVENTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "Bearing Degradation": {
        "action_title": "Reduce load by 20%, precision lubrication & scheduled bearing inspection",
        "load_reduction_pct": 20.0,
        "trend_damping_factor": 0.75,
        "vibration_decay_rate": 0.14,
        "temperature_cooling_rate": 0.45,
        "energy_recovery_pct": 65.0,
        "production_stabilization_pct": 70.0,
        "downtime_reduction_factor": 0.82,
        "description": "Reduces mechanical shear and friction, decelerating bearing raceway spalling and mitigating seizure risk."
    },
    "Motor Overheating": {
        "action_title": "De-rate duty cycle by 15%, clear ventilation ducts & schedule thermal diagnostics",
        "load_reduction_pct": 15.0,
        "trend_damping_factor": 0.80,
        "vibration_decay_rate": 0.08,
        "temperature_cooling_rate": 0.85,
        "energy_recovery_pct": 70.0,
        "production_stabilization_pct": 75.0,
        "downtime_reduction_factor": 0.85,
        "description": "Alleviates stator thermal saturation, prevents winding insulation breakdown, and reduces resistance losses."
    },
    "Cooling System Failure": {
        "action_title": "De-rate machine load by 15%, clear heat exchangers & purge coolant loop",
        "load_reduction_pct": 15.0,
        "trend_damping_factor": 0.80,
        "vibration_decay_rate": 0.05,
        "temperature_cooling_rate": 1.10,
        "energy_recovery_pct": 60.0,
        "production_stabilization_pct": 70.0,
        "downtime_reduction_factor": 0.80,
        "description": "Restores heat dissipation gradient and eliminates thermal expansion stress on internal tooling."
    },
    "Hydraulic Pressure Failure": {
        "action_title": "Reduce hydraulic demand by 10%, replace intake filters & repressurize reservoir",
        "load_reduction_pct": 10.0,
        "trend_damping_factor": 0.70,
        "vibration_decay_rate": 0.06,
        "pressure_recovery_rate": 0.80,
        "energy_recovery_pct": 55.0,
        "production_stabilization_pct": 65.0,
        "downtime_reduction_factor": 0.75,
        "description": "Stabilizes line pressure, prevents actuator cavitation, and restores hydraulic clamping force."
    },
    "Electrical Anomaly": {
        "action_title": "Rebalance phase distribution, inspect variable frequency drive & tighten bus connections",
        "load_reduction_pct": 10.0,
        "trend_damping_factor": 0.75,
        "energy_recovery_pct": 75.0,
        "production_stabilization_pct": 80.0,
        "downtime_reduction_factor": 0.80,
        "description": "Eliminates harmonic distortion, suppresses transient voltage spikes, and lowers excessive energy draw."
    },
    "Default": {
        "action_title": "Conservative machine de-rating by 10% & multi-point preventive maintenance inspection",
        "load_reduction_pct": 10.0,
        "trend_damping_factor": 0.60,
        "vibration_decay_rate": 0.06,
        "temperature_cooling_rate": 0.35,
        "energy_recovery_pct": 50.0,
        "production_stabilization_pct": 60.0,
        "downtime_reduction_factor": 0.70,
        "description": "General stabilization de-rating to contain progressive wear until the next scheduled maintenance shift."
    }
}


def _calculate_slope(values: List[float]) -> float:
    """
    Computes linear regression slope over chronological sequence of observations.
    Returns unit change per hour.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n)
    y = np.array(values, dtype=float)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def run_what_if_simulation(machine_id: str, timestamp: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a 24-hour What-If impact simulation comparing 'Intervene Now' vs 'Do Nothing'.
    """
    # 1. Validate machine existence
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise ValueError(f"Machine {machine_id} not found")

    # 2. Retrieve target / latest telemetry
    current_record = machine_service.get_latest_sensor_record(machine_id, timestamp=timestamp)
    if not current_record:
        raise ValueError(f"No sensor data found for Machine {machine_id}")

    actual_timestamp = str(current_record.get("timestamp", "Unknown"))

    # 3. Retrieve historical records for trend calculation
    sensor_history = machine_service.get_sensor_history(machine_id, timestamp=actual_timestamp, limit=10)
    maint_history = machine_service.get_machine_maintenance_history(machine_id, timestamp=actual_timestamp)

    # 4. Perform ML analysis
    ml_res = ml_service.analyze_machine(current_record)
    failure_prob = float(ml_res["failure_probability"])
    is_anomaly = bool(ml_res["anomaly"])
    
    risk_level = "LOW"
    if is_anomaly or failure_prob > 0.5:
        risk_level = "HIGH"
    elif failure_prob > 0.3:
        risk_level = "MEDIUM"

    # 5. Calculate historical trends
    if sensor_history and len(sensor_history) >= 2:
        vib_hist = [float(r.get("vibration_mm_s", 1.8)) for r in sensor_history]
        temp_hist = [float(r.get("temperature_c", 45.0)) for r in sensor_history]
        energy_hist = [float(r.get("energy_consumption_kwh", 70.0)) for r in sensor_history]
        press_hist = [float(r.get("pressure_bar", 120.0)) for r in sensor_history]
        prod_hist = [float(r.get("production_output_units", 110.0)) for r in sensor_history]

        slope_vib = _calculate_slope(vib_hist)
        slope_temp = _calculate_slope(temp_hist)
        slope_energy = _calculate_slope(energy_hist)
        slope_press = _calculate_slope(press_hist)
        slope_prod = _calculate_slope(prod_hist)

        base_vib = float(np.mean(vib_hist[:max(1, len(vib_hist) // 2)]))
        base_temp = float(np.mean(temp_hist[:max(1, len(temp_hist) // 2)]))
        base_energy = float(np.mean(energy_hist[:max(1, len(energy_hist) // 2)]))
        base_press = float(np.mean(press_hist[:max(1, len(press_hist) // 2)]))
        base_prod = float(np.mean(prod_hist[:max(1, len(prod_hist) // 2)]))

        trends = {
            "vibration_change": round(current_record.get("vibration_mm_s", base_vib) - base_vib, 2),
            "temperature_change": round(current_record.get("temperature_c", base_temp) - base_temp, 2),
            "energy_change": round(current_record.get("energy_consumption_kwh", base_energy) - base_energy, 2),
            "pressure_change": round(current_record.get("pressure_bar", base_press) - base_press, 2),
            "production_change": round(current_record.get("production_output_units", base_prod) - base_prod, 2)
        }
    else:
        slope_vib = 0.0
        slope_temp = 0.0
        slope_energy = 0.0
        slope_press = 0.0
        slope_prod = 0.0
        trends = {
            "vibration_change": 0.0,
            "temperature_change": 0.0,
            "energy_change": 0.0,
            "pressure_change": 0.0,
            "production_change": 0.0
        }

    # 6. Diagnose Root Cause via deterministic RCA
    rca_res = run_deterministic_rca(current_record, trends, sensor_history, maint_history)
    root_cause = rca_res.get("probable_root_cause")
    if not root_cause or root_cause == "Unknown Mechanical/Electrical Failure":
        # Fallback to candidate scores if present
        candidate_scores = rca_res.get("candidate_scores", {})
        if candidate_scores and max(candidate_scores.values(), default=0) > 0:
            root_cause = max(candidate_scores.items(), key=lambda x: x[1])[0]
        else:
            root_cause = "Default"

    # Select intervention profile
    profile = INTERVENTION_PROFILES.get(root_cause, INTERVENTION_PROFILES["Default"])

    # 7. Bound slopes to physically plausible hourly rates
    slope_vib = float(np.clip(slope_vib, -0.4, 0.6))
    slope_temp = float(np.clip(slope_temp, -1.5, 2.0))
    slope_energy = float(np.clip(slope_energy, -2.0, 2.5))
    slope_press = float(np.clip(slope_press, -3.0, 2.0))
    slope_prod = float(np.clip(slope_prod, -3.0, 1.0))

    # Active pre-failure degradation floors (if machine is already critical/anomalous)
    if failure_prob > 0.5 or is_anomaly:
        if root_cause == "Bearing Degradation":
            slope_vib = max(slope_vib, 0.12)
            slope_temp = max(slope_temp, 0.35)
            slope_energy = max(slope_energy, 0.40)
            slope_prod = min(slope_prod, -0.70)
        elif root_cause == "Motor Overheating":
            slope_temp = max(slope_temp, 0.65)
            slope_energy = max(slope_energy, 0.60)
            slope_vib = max(slope_vib, 0.05)
            slope_prod = min(slope_prod, -0.50)
        elif root_cause == "Cooling System Failure":
            slope_temp = max(slope_temp, 0.80)
            slope_energy = max(slope_energy, 0.45)
            slope_prod = min(slope_prod, -0.60)
        elif root_cause == "Hydraulic Pressure Failure":
            slope_press = min(slope_press, -0.90)
            slope_prod = min(slope_prod, -0.80)
        elif root_cause == "Electrical Anomaly":
            slope_energy = max(slope_energy, 0.90)
            slope_prod = min(slope_prod, -0.60)

    # 8. Base conditions
    curr_temp = float(current_record.get("temperature_c", 45.0))
    curr_vib = float(current_record.get("vibration_mm_s", 1.8))
    curr_press = float(current_record.get("pressure_bar", 120.0))
    curr_energy = float(current_record.get("energy_consumption_kwh", 70.0))
    curr_prod = int(current_record.get("production_output_units", 110))
    nominal_prod_target = 120.0
    nominal_energy = 70.0
    nominal_vib = 1.8
    nominal_temp = 45.0
    nominal_press = 120.0

    # Calculate initial Projected Risk Index (0–100 scale)
    vib_severity = max(0.0, curr_vib - 2.5) * 3.5
    temp_severity = max(0.0, curr_temp - 55.0) * 0.6
    anomaly_bump = 25.0 if is_anomaly else 0.0
    initial_risk_index = min(100.0, max(5.0, (failure_prob * 65.0) + anomaly_bump + vib_severity + temp_severity))

    # 9. Generate 24-Hour Scenarios
    do_nothing_trajectory = []
    intervene_trajectory = []

    # Scenario B: Do Nothing accumulators
    dn_loss_sum = 0.0
    dn_waste_sum = 0.0
    dn_downtime_sum = 0.0
    dn_warning_hours = 0
    dn_critical_hours = 0

    # Scenario A: Intervene Now accumulators
    int_loss_sum = 0.0
    int_waste_sum = 0.0
    int_downtime_sum = 0.0
    int_warning_hours = 0
    int_critical_hours = 0

    load_red_pct = profile["load_reduction_pct"]
    trend_damping = profile["trend_damping_factor"]
    intervene_prod_target = nominal_prod_target * (1.0 - (load_red_pct / 100.0))

    for h in range(1, 25):
        # -------------------------------------------------------------
        # SCENARIO B: DO NOTHING
        # Trajectory continues along unmitigated trend
        # -------------------------------------------------------------
        dn_vib = float(np.clip(curr_vib + slope_vib * h, 0.5, 35.0))
        dn_temp = float(np.clip(curr_temp + slope_temp * h, 15.0, 130.0))
        dn_energy = float(np.clip(curr_energy + slope_energy * h, 20.0, 250.0))
        dn_press = float(np.clip(curr_press + slope_press * h, 10.0, 200.0))
        dn_prod = float(np.clip(curr_prod + slope_prod * h, 0.0, 130.0))

        # Escalating risk index
        dn_risk = min(100.0, max(5.0, initial_risk_index + (0.95 * h)))

        # Impact calculations
        hourly_dn_loss = max(0.0, nominal_prod_target - dn_prod)
        hourly_dn_waste = max(0.0, dn_energy - nominal_energy)
        
        # Downtime exposure accumulation
        if dn_risk >= 70.0:
            hourly_dn_dt = 0.35  # High probability of forced outage
            dn_critical_hours += 1
            dn_warning_hours += 1
        elif dn_risk >= 40.0:
            hourly_dn_dt = 0.12  # Moderate degradation / micro-stoppages
            dn_warning_hours += 1
        else:
            hourly_dn_dt = 0.0

        dn_loss_sum += hourly_dn_loss
        dn_waste_sum += hourly_dn_waste
        dn_downtime_sum += hourly_dn_dt

        do_nothing_trajectory.append({
            "hour": h,
            "projected_risk_index": round(dn_risk, 1),
            "projected_temperature": round(dn_temp, 1),
            "projected_vibration": round(dn_vib, 2),
            "projected_energy": round(dn_energy, 1),
            "projected_production": int(round(dn_prod)),
            "projected_pressure": round(dn_press, 1)
        })

        # -------------------------------------------------------------
        # SCENARIO A: INTERVENE NOW
        # Trend is dampened, machine de-rated safely, sensors stabilize
        # -------------------------------------------------------------
        decay_factor = math.exp(-0.13 * h)
        int_vib = nominal_vib + max(0.0, curr_vib - nominal_vib) * decay_factor + (slope_vib * (1.0 - trend_damping) * h)
        int_vib = float(np.clip(int_vib, 0.5, 15.0))

        temp_decay = math.exp(-0.12 * h)
        int_temp = nominal_temp + max(0.0, curr_temp - nominal_temp) * temp_decay + (slope_temp * (1.0 - trend_damping) * h)
        int_temp = float(np.clip(int_temp, 15.0, 90.0))

        # Energy waste recovery
        excess_energy = max(0.0, curr_energy - nominal_energy)
        recovery_ratio = 1.0 - (profile["energy_recovery_pct"] / 100.0)
        int_energy = nominal_energy + (excess_energy * recovery_ratio * decay_factor)
        int_energy = float(np.clip(int_energy, 30.0, 150.0))

        press_decay = math.exp(-0.10 * h)
        int_press = nominal_press + (curr_press - nominal_press) * press_decay
        int_press = float(np.clip(int_press, 20.0, 180.0))

        # Production stabilizes at planned de-rated target without emergency stoppages
        int_prod = float(intervene_prod_target)

        # De-escalating risk index
        int_risk = max(18.0, (initial_risk_index * math.exp(-0.10 * h)) + 12.0)

        # Impact calculations
        hourly_int_loss = max(0.0, nominal_prod_target - int_prod)  # Controlled planned de-rate
        hourly_int_waste = max(0.0, int_energy - nominal_energy)

        if int_risk >= 70.0:
            hourly_int_dt = 0.08
            int_critical_hours += 1
            int_warning_hours += 1
        elif int_risk >= 40.0:
            hourly_int_dt = 0.02
            int_warning_hours += 1
        else:
            hourly_int_dt = 0.0

        int_loss_sum += hourly_int_loss
        int_waste_sum += hourly_int_waste
        int_downtime_sum += hourly_int_dt

        intervene_trajectory.append({
            "hour": h,
            "projected_risk_index": round(int_risk, 1),
            "projected_temperature": round(int_temp, 1),
            "projected_vibration": round(int_vib, 2),
            "projected_energy": round(int_energy, 1),
            "projected_production": int(round(int_prod)),
            "projected_pressure": round(int_press, 1)
        })

    # Avoided impact (Do Nothing minus Intervene Now)
    prod_avoided = max(0.0, dn_loss_sum - int_loss_sum)
    energy_avoided = max(0.0, dn_waste_sum - int_waste_sum)
    downtime_avoided = max(0.0, dn_downtime_sum - int_downtime_sum)

    current_downtime_risk_str = "Immediate Outage Risk" if risk_level == "HIGH" else ("Elevated Friction / Drift" if risk_level == "MEDIUM" else "Nominal")
    sim_result = {
        "machine_id": machine_id,
        "timestamp": actual_timestamp,
        "root_cause": root_cause,
        "current_state": {
            "risk_level": risk_level,
            "failure_probability": round(failure_prob, 3),
            "production": curr_prod,
            "energy": round(curr_energy, 1),
            "temperature_c": round(curr_temp, 1),
            "vibration_mm_s": round(curr_vib, 2),
            "pressure_bar": round(curr_press, 1),
            "anomaly": is_anomaly,
            "downtime_risk": current_downtime_risk_str
        },
        "assumptions": {
            "root_cause_profile": root_cause,
            "intervention_action": profile["action_title"],
            "load_reduction": f"{profile['load_reduction_pct']}% planned capacity de-rate",
            "trend_damping": f"{int(profile['trend_damping_factor'] * 100)}% trend deceleration",
            "energy_recovery": f"{int(profile['energy_recovery_pct'])}% friction energy waste mitigation",
            "production_stabilization": f"Stable throughput fixed at {int(round(intervene_prod_target))} units/hr",
            "baseline_reference": f"Nominal target: {int(nominal_prod_target)} units/hr, Energy baseline: {int(nominal_energy)} kWh",
            "horizon_hours": 24,
            "disclaimer": "Scenario estimate for decision support. Not a physical-world predictive guarantee."
        },
        "intervene_now": {
            "projected_risk_index": round(intervene_trajectory[-1]["projected_risk_index"], 1),
            "production_loss_units": round(int_loss_sum, 1),
            "energy_wastage_kwh": round(int_waste_sum, 1),
            "downtime_exposure_hours": round(int_downtime_sum, 1),
            "hours_above_warning": int_warning_hours,
            "hours_above_critical": int_critical_hours,
            "trajectory": intervene_trajectory
        },
        "do_nothing": {
            "projected_risk_index": round(do_nothing_trajectory[-1]["projected_risk_index"], 1),
            "production_loss_units": round(dn_loss_sum, 1),
            "energy_wastage_kwh": round(dn_waste_sum, 1),
            "downtime_exposure_hours": round(dn_downtime_sum, 1),
            "hours_above_warning": dn_warning_hours,
            "hours_above_critical": dn_critical_hours,
            "trajectory": do_nothing_trajectory
        },
        "estimated_difference": {
            "production_loss_avoided": round(prod_avoided, 1),
            "energy_wastage_avoided": round(energy_avoided, 1),
            "downtime_exposure_avoided": round(downtime_avoided, 1)
        }
    }

    try:
        from services.llm_service import get_llm_service
        sim_result["explanation"] = get_llm_service().explain_what_if(sim_result)
    except Exception:
        sim_result["explanation"] = (
            f"Intervening now vs. continuing current operation over the 24-hour horizon yields an estimated avoidance of "
            f"{prod_avoided:.0f} units in production loss, {energy_avoided:.1f} kWh in wasted energy, and "
            f"{downtime_avoided:.1f} hours of downtime exposure."
        )

    return sim_result

