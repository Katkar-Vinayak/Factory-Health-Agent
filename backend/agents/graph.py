from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from agents.monitoring_agent import monitoring_node
from agents.investigation_agent import investigation_node
from agents.rca_agent import rca_node
from agents.impact_agent import impact_node
from agents.decision_agent import decision_node
from agents.notification_agent import notification_node
from agents.verification_agent import verification_node
from agents.report_agent import report_node

def route_risk(state: AgentState) -> str:
    # Router logic: MEDIUM and HIGH risk machines proceed through full diagnostic investigation
    risk = str(state.get("risk_level", "LOW")).strip().upper()
    if risk in ("HIGH", "MEDIUM"):
        return "investigate"
    return "report"

# Build the Graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("monitoring", monitoring_node)
workflow.add_node("investigation", investigation_node)
workflow.add_node("rca", rca_node)
workflow.add_node("impact", impact_node)
workflow.add_node("decision", decision_node)
workflow.add_node("notification", notification_node)
workflow.add_node("verification", verification_node)
workflow.add_node("report", report_node)

# Add edges
workflow.add_edge(START, "monitoring")

workflow.add_conditional_edges(
    "monitoring",
    route_risk,
    {
        "investigate": "investigation",
        "report": "report"
    }
)

workflow.add_edge("investigation", "rca")
workflow.add_edge("rca", "impact")
workflow.add_edge("impact", "decision")
workflow.add_edge("decision", "notification")
workflow.add_edge("notification", "verification")
workflow.add_edge("verification", "report")
workflow.add_edge("report", END)

# Compile graph
app_graph = workflow.compile()

def run_agent_workflow(machine_id: str, timestamp: str = None) -> dict:
    initial_state = {
        "machine_id": machine_id,
        "timestamp": timestamp,
        "risk_level": "UNKNOWN",
        "sensor_data": None,
        "sensor_history": None,
        "energy_history": None,
        "sensor_trends": None,
        "ml_analysis": None,
        "maintenance_history": None,
        "production_history": None,
        "abnormal_signals": [],
        "candidate_scores": None,
        "root_cause": None,
        "evidence": [],
        "impact": None,
        "recommendation": None,
        "agent_trace": [],
        "investigation_explanation": None,
        "rca_explanation": None,
        "decision_explanation": None,
        "llm_status": None,
        "final_report": "",
        # HITL / Verification initial state
        "notification_id": None,
        "approval_status": "NOT_REQUIRED",
        "approved_by": None,
        "approved_at": None,
        "approved_actions": [],
        "action_records": [],
        "verification_status": "NOT_STARTED",
        "replacement_request": None,
        "vendor_information": None
    }
    
    # Run graph
    result_state = app_graph.invoke(initial_state)
    return result_state
    