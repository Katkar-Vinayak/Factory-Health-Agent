"""
Verification Agent for Factory Health & Response Agent
======================================================
LangGraph verification node.

STRICT CONSTRAINTS:
- NEVER creates approval.
- NEVER executes actions.
- Only verifies software action completion when valid action records exist.
- When no action records exist (initial analysis), leaves verification_status as 'NOT_STARTED'.
"""

from typing import Dict, Any, List
from agents.state import AgentState
from services import verification_service


def verification_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Inspects action records and verifies software completion.
    Safe for initial diagnostic requests (defaults to NOT_STARTED).
    """
    action_records = state.get("action_records") or []
    notif_id = state.get("notification_id")

    if not action_records and not notif_id:
        state["verification_status"] = "NOT_STARTED"
        state["agent_trace"].append("Verification Agent: Nominal state (Status: NOT_STARTED)")
        return state

    if not action_records:
        # Initial analysis before human approval
        state["verification_status"] = "NOT_STARTED"
        state["agent_trace"].append("Verification Agent: Awaiting human approval (Status: NOT_STARTED)")
        return state

    # Action records exist: verify software completion
    verified_count = 0
    latest_verification_status = "PENDING_TELEMETRY"

    for action in action_records:
        aid = action.get("action_id")
        atype = action.get("action_type")
        nid = action.get("notification_id") or notif_id

        if nid and aid:
            res = verification_service.verify_action_completion(
                notification_id=nid,
                action_id=aid,
                action_type=atype
            )
            if res.get("action_verified"):
                verified_count += 1
                latest_verification_status = res.get("verification_status", "PENDING_TELEMETRY")

    state["verification_status"] = latest_verification_status
    state["agent_trace"].append(
        f"Verification Agent: Verified {verified_count}/{len(action_records)} action records "
        f"(Status: {state['verification_status']})"
    )

    return state
