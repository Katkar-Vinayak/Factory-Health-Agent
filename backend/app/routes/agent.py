from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from services import agent_service
from services import machine_service

router = APIRouter(prefix="/agent", tags=["Agent"])

class AgentAnalyzeRequest(BaseModel):
    machine_id: str
    timestamp: Optional[str] = None

class AgentAnalyzeResponse(BaseModel):
    machine_id: str
    timestamp: Optional[str]
    risk_level: str
    failure_probability: float
    anomaly: bool
    root_cause: Optional[str] = None
    confidence: Optional[float] = None
    candidate_scores: Optional[Dict[str, float]] = None
    evidence: List[str] = []
    impact: Dict[str, Any] = {}
    recommendations: List[Dict[str, Any]] = []
    agent_trace: List[str] = []
    final_report: str = ""
    llm_status: Optional[Dict[str, Any]] = None
    investigation_explanation: Optional[str] = None
    rca_explanation: Optional[str] = None
    decision_explanation: Optional[str] = None
    notification_id: Optional[str] = None
    approval_status: Optional[str] = "NOT_REQUIRED"
    verification_status: Optional[str] = "NOT_STARTED"

@router.get("/model-status")
def get_model_status():
    """Returns local LLM singleton service status and hardware metrics."""
    from services.llm_service import get_llm_service
    return get_llm_service().get_status()

@router.post("/analyze", response_model=AgentAnalyzeResponse)
def analyze_machine(req: AgentAnalyzeRequest):
    machine = machine_service.get_machine(req.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine {req.machine_id} not found")
        
    try:
        result = agent_service.run_factory_analysis(req.machine_id, req.timestamp)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

