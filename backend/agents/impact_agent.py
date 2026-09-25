from agents.state import AgentState

def impact_node(state: AgentState) -> AgentState:
    state["agent_trace"].append("Impact Agent calculated production and energy impact")
    
    sensors = state.get("sensor_data", {})
    trends = state.get("sensor_trends", {})
    
    # 1. Production impact
    current_production = sensors.get("production_output_units", 110)
    baseline_production = 110
    if current_production < 85:
        prod_impact = f"Severe ({current_production} vs baseline {baseline_production} units)"
    elif current_production < 100:
        prod_impact = f"Moderate ({current_production} vs baseline {baseline_production} units)"
    else:
        prod_impact = f"Normal ({current_production} units)"
        
    # 2. Energy impact
    energy = sensors.get("energy_consumption_kwh", 72.0)
    baseline_energy = 72.0
    if energy > 88.0:
        energy_impact = f"High wastage (+{(energy - baseline_energy):.1f} kWh over baseline)"
    elif energy > 78.0:
        energy_impact = f"Elevated (+{(energy - baseline_energy):.1f} kWh over baseline)"
    else:
        energy_impact = f"Normal ({energy:.1f} kWh)"
        
    # 3. Urgency and Downtime Risk
    prob = float(state.get("ml_analysis", {}).get("failure_probability", 0.0))
    urgency = "HIGH" if prob >= 0.70 else ("MEDIUM" if prob >= 0.40 else "LOW")
    
    state["impact"] = {
        "production_impact": prod_impact,
        "energy_impact": energy_impact,
        "downtime_risk": f"{(prob * 100):.1f}% chance within 24h",
        "urgency": urgency
    }
    
    return state
