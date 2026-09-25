from langchain_core.prompts import ChatPromptTemplate
from agents.state import AgentState
from agents.llm import get_llm, extract_llm_text

def report_node(state: AgentState) -> AgentState:
    state["agent_trace"].append("Report Agent generated final report")
    
    machine_id = state["machine_id"]
    timestamp = state.get("timestamp") or (state.get("sensor_data") or {}).get("timestamp", "Unknown")
    risk_level = state.get("risk_level", "UNKNOWN")
    failure_prob = (state.get("ml_analysis") or {}).get("failure_probability", 0.0)
    anomaly = (state.get("ml_analysis") or {}).get("anomaly", False)
    root_cause_info = state.get("root_cause") or {}
    root_cause = root_cause_info.get("probable_root_cause", "None")
    confidence = root_cause_info.get("confidence", 0.0)
    evidence = state.get("evidence", [])
    impact = state.get("impact") or {}
    recommendation = state.get("recommendation") or {}
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an Industrial Reporting Assistant.
Summarize the machine investigation report concisely and clearly based ONLY on the provided structured data.
State the machine status, risk level, probable root cause with confidence, key evidence, operational impact, and recommended action.
Do not invent any measurements or equipment facts. Produce clean, professional markdown text."""),
        ("user", """
Machine ID: {machine_id}
Timestamp: {timestamp}
Risk Level: {risk_level}
Failure Probability: {failure_prob}
Anomaly Detected: {anomaly}
Probable Root Cause: {root_cause} (Confidence: {confidence})
Key Evidence: {evidence}
Operational Impact: {impact}
Action Plan: {recommendation}
""")
    ])
    
    try:
        llm = get_llm()
        chain = prompt | llm
        
        response = chain.invoke({
            "machine_id": machine_id,
            "timestamp": timestamp,
            "risk_level": risk_level,
            "failure_prob": f"{failure_prob:.2f}",
            "anomaly": anomaly,
            "root_cause": root_cause,
            "confidence": f"{confidence:.2f}",
            "evidence": evidence,
            "impact": impact,
            "recommendation": recommendation
        })
        
        state["final_report"] = extract_llm_text(response.content)
            
    except Exception as e:
        # High quality deterministic report fallback
        if risk_level == "LOW":
            state["final_report"] = (
                f"Machine {machine_id} operating under nominal parameters at {timestamp}. "
                f"Failure probability is {failure_prob:.2f} with no anomalies detected. Routine monitoring continues."
            )
        else:
            action_title = recommendation.get("action", "Schedule Diagnostic Inspection")
            state["final_report"] = (
                f"Machine {machine_id} identified as {risk_level} risk at {timestamp} "
                f"(Failure Probability: {failure_prob:.2f}). "
                f"Probable Root Cause: {root_cause} (Confidence: {confidence:.2f}). "
                f"Recommended Action: {action_title}."
            )
    
    return state
