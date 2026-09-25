from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.llm_service import get_llm_service

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    llm: Optional[Dict[str, Any]] = None

@router.get("/health", response_model=HealthResponse)
def health_check():
    svc = get_llm_service()
    return {"status": "ok", "llm": svc.get_status()}

