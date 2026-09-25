from agents.state import AgentState
from services.llm_service import get_llm_service

def report_node(state: AgentState) -> AgentState:
    state["agent_trace"].append("Report Agent generated final report")
    
    llm_svc = get_llm_service()
    
    try:
        final_rep = llm_svc.generate_final_report(state)
        state["final_report"] = final_rep
    except Exception as e:
        # High quality deterministic report fallback
        machine_id = state.get("machine_id", "Unknown")
        timestamp = state.get("timestamp") or (state.get("sensor_data") or {}).get("timestamp", "Unknown")
        risk_level = state.get("risk_level", "UNKNOWN")
        failure_prob = (state.get("ml_analysis") or {}).get("failure_probability", 0.0)
        root_cause_info = state.get("root_cause") or {}
        root_cause = root_cause_info.get("probable_root_cause", "None")
        confidence = root_cause_info.get("confidence", 0.0)
        recommendation = state.get("recommendation") or {}
        
        if risk_level == "LOW":
            state["final_report"] = (
                f"### Executive Health Summary: Machine {machine_id}\n\n"
                f"Machine {machine_id} operating under nominal parameters at {timestamp}. "
                f"Failure probability is {failure_prob:.2f} with no anomalies detected. Routine monitoring continues."
            )
        else:
            action_title = recommendation.get("action", "Schedule Diagnostic Inspection")
            state["final_report"] = (
                f"### Executive Health Summary: Machine {machine_id}\n\n"
                f"Machine {machine_id} identified as {risk_level} risk at {timestamp} "
                f"(Failure Probability: {failure_prob*100:.1f}%). "
                f"Probable Root Cause: {root_cause} (Confidence: {confidence*100:.0f}%). "
                f"Recommended Action: {action_title}."
            )

    # Append HITL operational status
    approval_status = state.get("approval_status", "NOT_REQUIRED")
    verification_status = state.get("verification_status", "NOT_STARTED")
    
    hitl_status_note = ""
    if approval_status == "PENDING":
        hitl_status_note = "\n\n**Operational Status**: Maintenance action pending human approval."
    elif approval_status == "APPROVED":
        if verification_status == "PENDING_TELEMETRY":
            hitl_status_note = (
                "\n\n**Operational Status**: Maintenance action approved and software execution completed. "
                "Software action verified; physical recovery remains pending new telemetry."
            )
        elif verification_status == "VERIFIED":
            hitl_status_note = "\n\n**Operational Status**: Maintenance action approved and verified. Machine health recovery confirmed."
        else:
            hitl_status_note = "\n\n**Operational Status**: Maintenance action approved and software execution completed."
    elif approval_status == "REJECTED":
        hitl_status_note = "\n\n**Operational Status**: Maintenance action rejected by human operator."

    if hitl_status_note and hitl_status_note.strip() not in state.get("final_report", ""):
        state["final_report"] = state.get("final_report", "") + hitl_status_note

    # Attach LLM singleton status
    state["llm_status"] = llm_svc.get_status()
    
    return state

