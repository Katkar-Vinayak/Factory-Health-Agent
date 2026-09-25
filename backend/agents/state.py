from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict, total=False):
    machine_id: str
    timestamp: Optional[str]
    
    # State flags
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    
    # Data gathered
    sensor_data: Optional[Dict[str, Any]]
    sensor_history: Optional[List[Dict[str, Any]]]
    energy_history: Optional[List[Dict[str, Any]]]
    sensor_trends: Optional[Dict[str, float]]
    ml_analysis: Optional[Dict[str, Any]]
    maintenance_history: Optional[List[Dict[str, Any]]]
    production_history: Optional[List[Dict[str, Any]]]
    
    # Inferred properties
    abnormal_signals: List[str]
    candidate_scores: Optional[Dict[str, float]]
    root_cause: Optional[Dict[str, Any]]  # e.g. {"probable_root_cause": "...", "confidence": 0.85, ...}
    evidence: List[str]
    impact: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    
    # Trace for debugging and verification
    agent_trace: List[str]
    
    # Final output
    final_report: str
