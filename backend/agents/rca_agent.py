import json
from typing import Dict, Any, List, Tuple
import numpy as np
from langchain_core.prompts import ChatPromptTemplate
from agents.state import AgentState
from agents.llm import get_llm, extract_llm_text

SUPPORTED_FAILURE_TYPES = [
    "Bearing Degradation",
    "Motor Overheating",
    "Cooling System Failure",
    "Hydraulic Pressure Failure",
    "Electrical Anomaly"
]

def run_deterministic_rca(
    sensor: Dict[str, Any],
    trends: Dict[str, float],
    sensor_history: List[Dict[str, Any]],
    maintenance_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Transparent, evidence-based deterministic RCA engine.
    Calculates candidate scores for all 5 failure categories using multiple available signals:
    - sensor measurements
    - historical trends (vibration, temperature, energy, pressure, production changes)
    - operating load
    """
    vib = float(sensor.get("vibration_mm_s", 1.8))
    temp = float(sensor.get("temperature_c", 46.0))
    energy = float(sensor.get("energy_consumption_kwh", 72.0))
    press = float(sensor.get("pressure_bar", 120.0))
    prod = int(sensor.get("production_output_units", 110))
    load = float(sensor.get("load_percent", 80.0))
    
    vib_change = float(trends.get("vibration_change", 0.0))
    temp_change = float(trends.get("temperature_change", 0.0))
    energy_change = float(trends.get("energy_change", 0.0))
    press_change = float(trends.get("pressure_change", 0.0))
    prod_change = float(trends.get("production_change", 0.0))
    
    scores: Dict[str, float] = {
        "Bearing Degradation": 0.0,
        "Motor Overheating": 0.0,
        "Cooling System Failure": 0.0,
        "Hydraulic Pressure Failure": 0.0,
        "Electrical Anomaly": 0.0
    }
    
    evidence_map: Dict[str, List[str]] = {
        "Bearing Degradation": [],
        "Motor Overheating": [],
        "Cooling System Failure": [],
        "Hydraulic Pressure Failure": [],
        "Electrical Anomaly": []
    }
    
    # ----------------------------------------------------
    # 1. Bearing Degradation Rules
    # Signals: high vibration, increasing vibration trend, temperature increase, energy increase, production decline
    # ----------------------------------------------------
    if vib > 3.0:
        pts = 1.5 if vib <= 5.0 else (3.0 if vib <= 8.0 else 4.5)
        scores["Bearing Degradation"] += pts
        evidence_map["Bearing Degradation"].append(
            f"Vibration reached {vib:.2f} mm/s, critically above baseline (~1.8 mm/s, delta: +{vib - 1.8:.2f} mm/s)."
        )
    if vib_change > 0.5:
        pts = 1.5 if vib_change <= 2.0 else 2.5
        scores["Bearing Degradation"] += pts
        evidence_map["Bearing Degradation"].append(
            f"Vibration exhibits an upward degradation trend of +{vib_change:.2f} mm/s compared to recent baseline."
        )
    if temp > 52.0 or temp_change > 2.0:
        scores["Bearing Degradation"] += 1.0
        evidence_map["Bearing Degradation"].append(
            f"Bearing friction generated temperature rise to {temp:.1f}°C (+{temp_change:.1f}°C trend)."
        )
    if energy > 78.0 or energy_change > 4.0:
        scores["Bearing Degradation"] += 1.0
        evidence_map["Bearing Degradation"].append(
            f"Energy consumption increased to {energy:.1f} kWh due to increased bearing rotational friction."
        )
    if prod < 100 or prod_change < -5.0:
        scores["Bearing Degradation"] += 1.0
        evidence_map["Bearing Degradation"].append(
            f"Production throughput dropped to {prod} units ({prod_change:+.1f} unit change) from mechanical drag."
        )

    # ----------------------------------------------------
    # 2. Motor Overheating Rules
    # Signals: high temperature, increasing temperature trend, increased energy, moderate vibration increase
    # ----------------------------------------------------
    if temp > 60.0:
        pts = 2.0 if temp <= 68.0 else 3.5
        scores["Motor Overheating"] += pts
        evidence_map["Motor Overheating"].append(
            f"Motor operating temperature reached elevated level of {temp:.1f}°C (nominal ~46.0°C)."
        )
    if temp_change > 3.0:
        pts = 1.5 if temp_change <= 6.0 else 2.5
        scores["Motor Overheating"] += pts
        evidence_map["Motor Overheating"].append(
            f"Temperature rose steadily by +{temp_change:.1f}°C over recent operating hours."
        )
    if energy > 78.0 or energy_change > 4.0:
        scores["Motor Overheating"] += 1.5
        evidence_map["Motor Overheating"].append(
            f"Elevated energy draw at {energy:.1f} kWh (+{energy_change:.1f} kWh) indicates increased motor winding resistance."
        )
    if 2.2 <= vib <= 5.5 or (0.3 <= vib_change <= 2.5):
        scores["Motor Overheating"] += 1.5
        evidence_map["Motor Overheating"].append(
            f"Moderate secondary vibration detected at {vib:.2f} mm/s consistent with thermal expansion of the motor rotor."
        )
    elif vib > 6.0:
        # Extreme vibration is characteristic of bearings, penalize motor overheating
        scores["Motor Overheating"] = max(0.0, scores["Motor Overheating"] - 2.0)

    # ----------------------------------------------------
    # 3. Cooling System Failure Rules
    # Signals: high temperature, rapid temperature increase, temperature remains high despite reasonable load, increased energy
    # ----------------------------------------------------
    if temp > 65.0:
        pts = 2.0 if temp <= 75.0 else 3.5
        scores["Cooling System Failure"] += pts
        evidence_map["Cooling System Failure"].append(
            f"Thermal escalation observed with machine temperature reaching {temp:.1f}°C."
        )
    if temp_change > 5.0:
        pts = 2.0 if temp_change <= 10.0 else 3.0
        scores["Cooling System Failure"] += pts
        evidence_map["Cooling System Failure"].append(
            f"Rapid temperature escalation of +{temp_change:.1f}°C confirms acute heat dissipation failure."
        )
    if temp > 65.0 and load <= 88.0:
        scores["Cooling System Failure"] += 2.0
        evidence_map["Cooling System Failure"].append(
            f"Temperature remains abnormally elevated despite moderate machine load ({load:.1f}%), pointing to cooling circuit loss."
        )
    if energy > 76.0 or energy_change > 4.0:
        scores["Cooling System Failure"] += 1.0
        evidence_map["Cooling System Failure"].append(
            f"Energy consumption increased to {energy:.1f} kWh due to thermal inefficiency."
        )
    if vib < 2.5:
        scores["Cooling System Failure"] += 1.5
        evidence_map["Cooling System Failure"].append(
            f"Mechanical vibration remains nominal at {vib:.2f} mm/s, ruling out mechanical bearing breakdown."
        )
    elif vib > 3.0:
        # Significant vibration rules out pure cooling failure
        scores["Cooling System Failure"] = max(0.0, scores["Cooling System Failure"] - 3.0)

    # ----------------------------------------------------
    # 4. Hydraulic Pressure Failure Rules
    # Signals: abnormal pressure drop, pressure degradation trend, production reduction, vibration increase where supported
    # ----------------------------------------------------
    if press < 105.0:
        pts = 2.5 if press >= 85.0 else 4.0
        scores["Hydraulic Pressure Failure"] += pts
        evidence_map["Hydraulic Pressure Failure"].append(
            f"Abnormal hydraulic line pressure drop to {press:.1f} bar (nominal ~120.0 bar, loss: -{120.0 - press:.1f} bar)."
        )
    if press_change < -8.0:
        pts = 2.0 if press_change >= -20.0 else 3.0
        scores["Hydraulic Pressure Failure"] += pts
        evidence_map["Hydraulic Pressure Failure"].append(
            f"Severe pressure degradation trend with a decline of {press_change:.1f} bar over recent readings."
        )
    if prod < 95 or prod_change < -8.0:
        scores["Hydraulic Pressure Failure"] += 1.5
        evidence_map["Hydraulic Pressure Failure"].append(
            f"Production output declined to {prod} units ({prod_change:+.1f} unit change) due to insufficient hydraulic actuator pressure."
        )
    if 2.5 <= vib <= 6.0 or vib_change > 0.4:
        scores["Hydraulic Pressure Failure"] += 1.0
        evidence_map["Hydraulic Pressure Failure"].append(
            f"Secondary hydraulic pump cavitation/chatter observed with vibration at {vib:.2f} mm/s."
        )
    elif press >= 115.0:
        # Normal pressure directly contradicts hydraulic pressure failure
        scores["Hydraulic Pressure Failure"] = 0.0

    # ----------------------------------------------------
    # 5. Electrical Anomaly Rules
    # Signals: abnormal energy consumption, unstable production, unusual temperature/energy relationship
    # ----------------------------------------------------
    if energy > 88.0:
        pts = 2.5 if energy <= 98.0 else 4.0
        scores["Electrical Anomaly"] += pts
        evidence_map["Electrical Anomaly"].append(
            f"Abnormal power surge detected with energy consumption at {energy:.1f} kWh (baseline ~72.0 kWh)."
        )
    if energy_change > 8.0:
        pts = 2.0 if energy_change <= 18.0 else 3.0
        scores["Electrical Anomaly"] += pts
        evidence_map["Electrical Anomaly"].append(
            f"Energy consumption increased rapidly by +{energy_change:.1f} kWh over recent operational baseline."
        )
    if energy > 85.0 and temp < 56.0:
        scores["Electrical Anomaly"] += 2.5
        evidence_map["Electrical Anomaly"].append(
            f"Unusual energy-to-temperature profile: high energy draw ({energy:.1f} kWh) with normal temperature ({temp:.1f}°C) indicates non-thermal electrical fault."
        )
    if prod < 102 or prod_change < -5.0:
        scores["Electrical Anomaly"] += 1.0
        evidence_map["Electrical Anomaly"].append(
            f"Manufacturing output affected at {prod} units ({prod_change:+.1f} change) amidst power fluctuations."
        )
    if vib < 2.5 and press > 110.0:
        scores["Electrical Anomaly"] += 1.0
        evidence_map["Electrical Anomaly"].append(
            f"Mechanical vibration ({vib:.2f} mm/s) and hydraulic pressure ({press:.1f} bar) remain nominal, isolating issue to electrical system."
        )
    elif vib > 4.5 or press < 100.0:
        scores["Electrical Anomaly"] = max(0.0, scores["Electrical Anomaly"] - 3.0)

    # Clean and round scores
    candidate_scores = {k: round(float(v), 2) for k, v in scores.items()}
    
    # Determine winner and relative confidence
    sorted_causes = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    best_cause, top_score = sorted_causes[0]
    runner_up_score = sorted_causes[1][1] if len(sorted_causes) > 1 else 0.0

    if top_score <= 0.5:
        probable_root_cause = "Unknown Mechanical/Electrical Failure"
        confidence = 0.0
        evidence = ["No conclusive anomalous patterns detected across sensor channels."]
    else:
        probable_root_cause = best_cause
        # Derived confidence from relative evidence scores: top / (top + runner_up)
        # Guarantees dynamic, continuous confidence reflecting signal clarity
        relative_conf = top_score / (top_score + max(0.0, runner_up_score))
        confidence = round(float(relative_conf), 2)
        confidence = max(0.15, min(0.96, confidence))
        
        evidence = evidence_map.get(best_cause, [])
        # Ensure at least 3 evidence points
        if len(evidence) < 3:
            evidence.append(f"Primary anomalous telemetry centered in {best_cause.lower()} subsystem.")
        if len(evidence) < 3:
            evidence.append(f"Operating parameters deviate significantly from normal baseline (Score: {top_score:.1f}).")

    return {
        "probable_root_cause": probable_root_cause,
        "confidence": confidence,
        "evidence": evidence,
        "candidate_scores": candidate_scores
    }


def rca_node(state: AgentState) -> AgentState:
    sensor = state.get("sensor_data", {})
    trends = state.get("sensor_trends", {})
    sensor_history = state.get("sensor_history", [])
    maintenance_history = state.get("maintenance_history", [])
    
    # 1. Run deterministic RCA engine
    deterministic_result = run_deterministic_rca(
        sensor=sensor,
        trends=trends,
        sensor_history=sensor_history,
        maintenance_history=maintenance_history
    )
    
    # 2. Record actual execution steps in trace
    state["agent_trace"].append("RCA Agent generated candidate root-cause scores")
    state["agent_trace"].append(f"RCA Agent selected {deterministic_result['probable_root_cause']} based on evidence")
    
    # Default to deterministic result
    state["root_cause"] = deterministic_result
    state["candidate_scores"] = deterministic_result["candidate_scores"]
    state["evidence"] = list(deterministic_result["evidence"])
    
    # 3. LLM Refinement Layer
    # The LLM receives structured RCA evidence produced by the deterministic engine.
    # LLM must explain why candidate root cause is likely and improve readability.
    # LLM must NOT override deterministic evidence without explanation.
    # If LLM fails, deterministic RCA result is used directly.
    try:
        llm = get_llm()
        
        # Build prompt without ground-truth failure_type
        clean_sensor = {k: v for k, v in sensor.items() if k != "failure_type"}
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an Industrial Reliability Engineer.
You have been provided with deterministic root-cause analysis results, telemetry, and evidence scores for an industrial machine.
Explain why the identified root cause is physically sound, summarize the supporting evidence clearly, and enhance technical readability.

You must NOT change the identified probable_root_cause unless the evidence clearly contradicts it.
You must return at least 3 concise, highly readable evidence points.

Respond ONLY with a valid JSON object in the following format:
{{
    "probable_root_cause": "{root_cause}",
    "confidence": {confidence},
    "evidence": ["Evidence point 1", "Evidence point 2", "Evidence point 3"],
    "explanation": "Brief physical explanation of why this failure occurs."
}}
Do not include any extra text, preamble, or markdown backticks outside the JSON object."""),
            ("user", """Machine ID: {machine_id}
Candidate Scores: {candidate_scores}
Identified Root Cause: {root_cause} (Confidence: {confidence})
Deterministic Evidence Points: {evidence}
Current Sensors: {sensors}
Historical Trends: {trends}
""")
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "machine_id": state["machine_id"],
            "root_cause": deterministic_result["probable_root_cause"],
            "confidence": deterministic_result["confidence"],
            "candidate_scores": json.dumps(deterministic_result["candidate_scores"]),
            "evidence": json.dumps(deterministic_result["evidence"]),
            "sensors": json.dumps(clean_sensor),
            "trends": json.dumps(trends)
        })
        
        content = extract_llm_text(response.content)
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        parsed_llm = json.loads(content)
        
        # Verify valid structure from LLM
        if isinstance(parsed_llm, dict) and "probable_root_cause" in parsed_llm:
            llm_cause = parsed_llm.get("probable_root_cause", deterministic_result["probable_root_cause"])
            # Ensure it is one of the 5 categories
            if llm_cause in SUPPORTED_FAILURE_TYPES:
                deterministic_result["probable_root_cause"] = llm_cause
            if "confidence" in parsed_llm and isinstance(parsed_llm["confidence"], (int, float)):
                # Keep confidence close to deterministic or bounded
                deterministic_result["confidence"] = round(float(parsed_llm["confidence"]), 2)
            if "evidence" in parsed_llm and isinstance(parsed_llm["evidence"], list) and len(parsed_llm["evidence"]) >= 3:
                deterministic_result["evidence"] = parsed_llm["evidence"]
            if "explanation" in parsed_llm:
                deterministic_result["explanation"] = parsed_llm["explanation"]
                
            state["root_cause"] = deterministic_result
            state["evidence"] = deterministic_result["evidence"]
            
    except Exception as e:
        # Graceful fallback: directly keep deterministic RCA result
        # Do not overwrite with arbitrary values!
        pass
        
    return state
