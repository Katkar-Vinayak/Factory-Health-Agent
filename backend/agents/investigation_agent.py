import numpy as np
from agents.state import AgentState
from agents.tools import (
    get_sensor_history,
    get_maintenance_history,
    get_production_history,
    get_energy_history
)

def investigation_node(state: AgentState) -> AgentState:
    machine_id = state["machine_id"]
    timestamp = state.get("timestamp") or (state.get("sensor_data") or {}).get("timestamp")
    
    # 1. Retrieve recent sensor history to calculate trends
    sensor_history = get_sensor_history(machine_id, timestamp, limit=10)
    state["sensor_history"] = sensor_history
    state["agent_trace"].append("Investigation Agent retrieved recent sensor history")
    
    # Calculate historical sensor trends (current reading vs earlier baseline)
    current_sensor = state.get("sensor_data") or (sensor_history[-1] if sensor_history else {})
    trends = {
        "vibration_change": 0.0,
        "temperature_change": 0.0,
        "energy_change": 0.0,
        "pressure_change": 0.0,
        "production_change": 0.0
    }
    
    if len(sensor_history) >= 2:
        # Use baseline from earliest records in recent window to see progression
        baseline_records = sensor_history[:max(1, len(sensor_history) // 2)]
        base_vib = float(np.mean([r.get("vibration_mm_s", 1.8) for r in baseline_records]))
        base_temp = float(np.mean([r.get("temperature_c", 46.0) for r in baseline_records]))
        base_energy = float(np.mean([r.get("energy_consumption_kwh", 72.0) for r in baseline_records]))
        base_pressure = float(np.mean([r.get("pressure_bar", 120.0) for r in baseline_records]))
        base_prod = float(np.mean([r.get("production_output_units", 110.0) for r in baseline_records]))
        
        trends["vibration_change"] = round(current_sensor.get("vibration_mm_s", base_vib) - base_vib, 2)
        trends["temperature_change"] = round(current_sensor.get("temperature_c", base_temp) - base_temp, 2)
        trends["energy_change"] = round(current_sensor.get("energy_consumption_kwh", base_energy) - base_energy, 2)
        trends["pressure_change"] = round(current_sensor.get("pressure_bar", base_pressure) - base_pressure, 2)
        trends["production_change"] = round(current_sensor.get("production_output_units", base_prod) - base_prod, 2)
        
    state["sensor_trends"] = trends
    
    # 2. Retrieve maintenance history
    maintenance = get_maintenance_history(machine_id, timestamp)
    state["maintenance_history"] = maintenance
    state["agent_trace"].append("Investigation Agent retrieved maintenance history")
    
    # 3. Retrieve production history
    production = get_production_history(machine_id, timestamp, limit=10)
    state["production_history"] = production
    state["agent_trace"].append("Investigation Agent retrieved production history")
    
    # 4. Selectively retrieve energy history if energy / electrical anomaly signals are present
    abnormal_signals = state.get("abnormal_signals", [])
    has_energy_signal = any("energy" in s.lower() or "power" in s.lower() for s in abnormal_signals)
    if has_energy_signal or abs(trends.get("energy_change", 0.0)) > 5.0 or current_sensor.get("energy_consumption_kwh", 0) > 80:
        energy_hist = get_energy_history(machine_id, timestamp, limit=10)
        state["energy_history"] = energy_hist
        state["agent_trace"].append("Investigation Agent retrieved energy history")
        
    return state
