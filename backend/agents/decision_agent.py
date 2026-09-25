import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from agents.state import AgentState
from agents.llm import get_llm, extract_llm_text

def generate_deterministic_decision(
    root_cause: str,
    confidence: float,
    failure_probability: float,
    urgency: str,
    production_impact: str,
    energy_impact: str,
    maintenance_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Transparent, safety-compliant deterministic decision engine.
    Produces actionable recommendations tailored to the specific root cause and impact.
    Strictly framed as decision-support recommendations (inspect, schedule, reduce load, monitor, shift production).
    """
    # 1. Determine priority
    if failure_probability >= 0.75 or urgency == "HIGH":
        priority = "HIGH"
    elif failure_probability >= 0.40:
        priority = "MEDIUM"
    else:
        priority = "LOW"
        
    # 2. Determine cost impact
    if failure_probability > 0.60 or "Severe" in str(production_impact) or "High" in str(energy_impact):
        estimated_cost_impact = "High"
    elif failure_probability > 0.30:
        estimated_cost_impact = "Medium"
    else:
        estimated_cost_impact = "Low"

    # 3. Generate tailored action plan based on root cause
    if root_cause == "Bearing Degradation":
        action = "Schedule Bearing Inspection and Reduce Machine Load"
        actions = [
            "Schedule precision ultrasonic vibration inspection of the bearing assembly.",
            "Reduce machine operating load by 20% to decelerate bearing raceway wear.",
            "Monitor high-frequency vibration and bearing temperature hourly.",
            "Shift non-critical production volume to alternate production lines if degradation accelerates."
        ]
        details = (
            f"Bearing degradation identified with {confidence*100:.0f}% confidence and {failure_probability*100:.0f}% "
            f"failure probability. Immediate load reduction is recommended to prevent mechanical seizure while maintenance is scheduled."
        )

    elif root_cause == "Motor Overheating":
        action = "Inspect Motor Cooling and Reduce Operating Duty Cycle"
        actions = [
            "Inspect motor ventilation grilles, cooling fan operation, and heat sink cleanliness.",
            "Reduce motor operating duty cycle and load to alleviate thermal saturation.",
            "Verify motor electrical winding insulation resistance and connection terminals.",
            "Schedule preventive motor thermal diagnostic inspection during the next scheduled shift change."
        ]
        details = (
            f"Motor overheating detected with {confidence*100:.0f}% confidence. Thermal stress requires "
            f"load de-rating and thorough cooling air path verification to safeguard stator windings."
        )

    elif root_cause == "Cooling System Failure":
        action = "Inspect Cooling Circuit and Monitor Thermal Levels"
        actions = [
            "Inspect coolant supply pumps, fluid levels, and delivery line valves for flow restrictions.",
            "Reduce operational machine load to minimize ongoing internal heat generation.",
            "Check heat exchanger radiators and fluid filters for fouling or contamination.",
            "Schedule expedited cooling circuit servicing and fluid replenishment."
        ]
        details = (
            f"Cooling system failure diagnosed with {confidence*100:.0f}% confidence. Temperature remains high "
            f"despite moderate loading, indicating heat dissipation failure requiring coolant circuit inspection."
        )

    elif root_cause == "Hydraulic Pressure Failure":
        action = "Inspect Hydraulic System and Address Pressure Loss"
        actions = [
            "Inspect hydraulic hoses, valve manifolds, and cylinder seals for external leaks or pressure bypass.",
            "Check hydraulic reservoir fluid levels, filter status, and pump operating discharge.",
            "Reduce hydraulic feed pressure and operational load to avoid actuator stalling.",
            "Schedule hydraulic pump inspection and filter element replacement."
        ]
        details = (
            f"Hydraulic pressure loss identified with {confidence*100:.0f}% confidence. Pressure collapse "
            f"directly threatens actuator force and manufacturing tolerances, requiring prompt hydraulic subsystem inspection."
        )

    elif root_cause == "Electrical Anomaly":
        action = "Inspect Electrical Distribution and Power Supply"
        actions = [
            "Inspect main power supply connections, circuit breakers, and phase balance for voltage irregularity.",
            "Conduct power quality logging to identify transient voltage spikes or harmonic distortion.",
            "Isolate sensitive auxiliary circuits and monitor real-time energy consumption.",
            "Schedule certified electrical technician diagnostic inspection prior to subsequent high-load production."
        ]
        details = (
            f"Electrical anomaly detected with {confidence*100:.0f}% confidence. Disproportionate power draw "
            f"without commensurate thermal friction warrants electrical circuit verification to avert component damage."
        )

    else:
        action = "Schedule Diagnostic System Inspection"
        actions = [
            "Perform comprehensive sensor verification and calibration check.",
            "Monitor live machine telemetry across all channels for emerging anomalies.",
            "Review past maintenance logs for recurring historical failure signatures."
        ]
        details = "Telemetry indicates anomalous operating behavior. General diagnostic inspection recommended."

    return {
        "action": action,
        "priority": priority,
        "recommended_actions": actions,
        "details": details,
        "estimated_cost_impact": estimated_cost_impact
    }


def decision_node(state: AgentState) -> AgentState:
    root_cause_data = state.get("root_cause") or {}
    probable_root_cause = root_cause_data.get("probable_root_cause", "Unknown Mechanical/Electrical Failure")
    confidence = float(root_cause_data.get("confidence", 0.0))
    failure_prob = float(state.get("ml_analysis", {}).get("failure_probability", 0.0))
    impact_data = state.get("impact") or {}
    urgency = impact_data.get("urgency", "MEDIUM")
    prod_impact = impact_data.get("production_impact", "Normal")
    energy_impact = impact_data.get("energy_impact", "Normal")
    maint_hist = state.get("maintenance_history", [])
    
    # 1. Generate deterministic action plan
    deterministic_decision = generate_deterministic_decision(
        root_cause=probable_root_cause,
        confidence=confidence,
        failure_probability=failure_prob,
        urgency=urgency,
        production_impact=prod_impact,
        energy_impact=energy_impact,
        maintenance_history=maint_hist
    )
    
    # 2. Add actual execution step to trace
    state["agent_trace"].append("Decision Agent generated maintenance and energy actions")
    state["recommendation"] = deterministic_decision
    
    # 3. Qwen Decision Explanation Layer
    # Explains operational reasoning behind the deterministic recommendation, urgency, and expected benefit
    try:
        from services.llm_service import get_llm_service
        llm_svc = get_llm_service()
        decision_expl = llm_svc.explain_decision(
            machine_id=state["machine_id"],
            root_cause=probable_root_cause,
            recommendation=deterministic_decision,
            impact=impact_data
        )
        state["decision_explanation"] = decision_expl
        state["recommendation"]["explanation"] = decision_expl
    except Exception:
        state["decision_explanation"] = None
        
    return state

