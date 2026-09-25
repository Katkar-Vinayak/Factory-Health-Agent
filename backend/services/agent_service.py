import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent_workflow

def run_factory_analysis(machine_id: str, timestamp: str = None) -> dict:
    """
    Invokes the LangGraph workflow for a given machine and optional timestamp.
    Returns the structured result.
    """
    result_state = run_agent_workflow(machine_id, timestamp)
    
    root_cause_dict = result_state.get("root_cause") or {}
    root_cause = root_cause_dict.get("probable_root_cause")
    confidence = root_cause_dict.get("confidence")
    candidate_scores = result_state.get("candidate_scores") or root_cause_dict.get("candidate_scores")
    
    return {
        "machine_id": result_state["machine_id"],
        "timestamp": (result_state.get("sensor_data") or {}).get("timestamp", timestamp),
        "risk_level": result_state.get("risk_level"),
        "failure_probability": (result_state.get("ml_analysis") or {}).get("failure_probability", 0.0),
        "anomaly": (result_state.get("ml_analysis") or {}).get("anomaly", False),
        "root_cause": root_cause,
        "confidence": confidence,
        "candidate_scores": candidate_scores,
        "evidence": result_state.get("evidence") or [],
        "impact": result_state.get("impact") or {},
        "recommendations": [result_state.get("recommendation")] if result_state.get("recommendation") else [],
        "agent_trace": result_state.get("agent_trace", []),
        "final_report": result_state.get("final_report", "")
    }
