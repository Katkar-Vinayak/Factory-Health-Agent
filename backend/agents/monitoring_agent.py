import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.state import AgentState
from agents.tools import get_machine_data
from services import ml_service

def monitoring_node(state: AgentState) -> AgentState:
    machine_id = state["machine_id"]
    timestamp = state.get("timestamp")
    
    # 1. Retrieve the relevant sensor record
    record = get_machine_data(machine_id, timestamp)
    if not record:
        state["agent_trace"].append(f"Monitoring Agent failed to find sensor data for {machine_id}")
        state["risk_level"] = "UNKNOWN"
        return state
        
    state["sensor_data"] = record
    
    # 2. Run the ML models
    analysis = ml_service.analyze_machine(record)
    state["ml_analysis"] = analysis
    
    # 3. Determine risk level and abnormal signals
    is_anomaly = analysis["anomaly"]
    prob = analysis["failure_probability"]
    
    abnormal_signals = []
    if record.get("temperature_c", 0) > 55.0:
        abnormal_signals.append(f"High temperature ({record['temperature_c']} °C)")
    if record.get("vibration_mm_s", 0) > 3.0:
        abnormal_signals.append(f"High vibration ({record['vibration_mm_s']} mm/s)")
    if record.get("pressure_bar", 120.0) < 105.0:
        abnormal_signals.append(f"Abnormal low pressure ({record['pressure_bar']} bar)")
    if record.get("energy_consumption_kwh", 0) > 85.0:
        abnormal_signals.append(f"Elevated energy consumption ({record['energy_consumption_kwh']} kWh)")
    if record.get("production_output_units", 110) < 95:
        abnormal_signals.append(f"Reduced production ({record['production_output_units']} units)")
    
    state["abnormal_signals"] = abnormal_signals
    
    state["agent_trace"].append("Monitoring Agent analyzed sensor data")
    if is_anomaly or prob > 0.5:
        state["risk_level"] = "HIGH"
        state["agent_trace"].append(f"High failure risk detected (Probability: {prob:.2f})")
    elif prob > 0.3:
        state["risk_level"] = "MEDIUM"
        state["agent_trace"].append(f"Medium failure risk detected (Probability: {prob:.2f})")
    else:
        state["risk_level"] = "LOW"
        state["agent_trace"].append(f"Normal operation detected (Probability: {prob:.2f})")

    return state
