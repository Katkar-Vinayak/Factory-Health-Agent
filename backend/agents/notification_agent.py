"""
Notification Agent for Factory Health & Response Agent
======================================================
Prepares persistent notification context and sets the PENDING approval state
for anomalous machine conditions during the LangGraph diagnostic workflow.

CRITICAL ARCHITECTURAL CONSTRAINTS:
- Asynchronous HITL: Never blocks the HTTP analysis request.
- Strictly links or registers a persistent notification in PENDING status.
- Zero automatic action execution.
- Leverages deterministic RCA subsystem mapping for component resolution.
"""

from typing import Dict, Any, List, Optional
from agents.state import AgentState
from services import notification_service

# Deterministic root cause to component mapping
ROOT_CAUSE_COMPONENT_MAP = {
    "Bearing Degradation": "Bearing",
    "Motor Overheating": "Motor",
    "Cooling System Failure": "Cooling Pump",
    "Hydraulic Pressure Failure": "Hydraulic Valve",
    "Electrical Anomaly": "Inverter & Phase Relay"
}


def notification_node(state: AgentState) -> AgentState:
    """
    LangGraph node: creates or associates a persistent notification for HIGH/MEDIUM risk states.
    Sets approval_status to 'PENDING' without blocking for human input.
    """
    risk_level = str(state.get("risk_level", "UNKNOWN")).strip().upper()
    recommendation = state.get("recommendation") or {}
    priority = str(recommendation.get("priority", "LOW")).strip().upper()

    # Check if this machine state requires an operator notification
    if risk_level in ("HIGH", "MEDIUM") or priority in ("HIGH", "MEDIUM"):
        root_cause_data = state.get("root_cause") or {}
        probable_root_cause = str(root_cause_data.get("probable_root_cause", "Mechanical/Thermal Anomaly")).strip()
        
        # Determine component
        component = ROOT_CAUSE_COMPONENT_MAP.get(probable_root_cause, "General Subsystem")
        
        ml_analysis = state.get("ml_analysis") or {}
        failure_prob = float(ml_analysis.get("failure_probability", 0.0))
        machine_id = str(state.get("machine_id", "Unknown")).strip()
        timestamp = state.get("timestamp") or (state.get("sensor_data") or {}).get("timestamp")

        title = f"{risk_level} Risk: {probable_root_cause}"
        message = recommendation.get("details", f"Predictive model flagged {risk_level} risk condition.")
        actions_list = recommendation.get("recommended_actions", [recommendation.get("action", "Inspect machine")])

        # Register or retrieve existing notification with deduplication protection
        notif = notification_service.create_notification(
            machine_id=machine_id,
            severity=priority if priority in ("HIGH", "CRITICAL") else risk_level,
            title=title,
            message=message,
            component=component,
            root_cause=probable_root_cause,
            failure_probability=failure_prob,
            recommendation=actions_list,
            timestamp=timestamp
        )

        notif_id = notif.get("notification_id")
        notif_status = notif.get("status", "PENDING")

        state["notification_id"] = notif_id
        state["approval_status"] = "PENDING" if notif_status in ("PENDING", "ACTION_IN_PROGRESS", "VERIFICATION_PENDING") else notif_status
        state["vendor_information"] = notification_service.find_vendor_by_component(component)
        state["agent_trace"].append(f"Notification Agent: Notification {notif_id} registered (Status: {state['approval_status']})")

    else:
        # Healthy nominal machine: no notification or human approval needed
        state["notification_id"] = None
        state["approval_status"] = "NOT_REQUIRED"
        state["verification_status"] = "NOT_STARTED"
        state["agent_trace"].append("Notification Agent: Nominal state - operator approval not required")

    return state
