from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.schemas import WhatIfSimulationRequest
from services import simulation_service

router = APIRouter(prefix="/simulation", tags=["Simulation"])

@router.post("/what-if")
def simulate_what_if(payload: WhatIfSimulationRequest) -> Dict[str, Any]:
    """
    Simulates a 24-hour operational comparison between Intervene Now and Do Nothing
    for the specified machine and optional timestamp.
    """
    try:
        result = simulation_service.run_what_if_simulation(
            machine_id=payload.machine_id,
            timestamp=payload.timestamp
        )
        return result
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=422, detail=err_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")
