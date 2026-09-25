from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.schemas import MachineAnalysisResponse, AddMachineRequest, AddMachineResponse
from services import machine_service
from services import ml_service

router = APIRouter(prefix="/machines", tags=["Machines"])

@router.get("/", response_model=List[Dict[str, Any]])
def get_all_machines():
    return machine_service.get_all_machines()

@router.post("/add", response_model=AddMachineResponse)
def add_machine(payload: AddMachineRequest):
    try:
        result = machine_service.add_new_machine(payload.model_dump())
        return result
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add machine: {str(e)}")


@router.get("/{machine_id}")
def get_machine(machine_id: str):
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
    
    latest_sensor = machine_service.get_latest_sensor_record(machine_id)
    return {
        "metadata": machine,
        "latest_sensor": latest_sensor
    }

@router.get("/{machine_id}/analysis")
def get_machine_analysis(machine_id: str):
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
        
    latest_sensor = machine_service.get_latest_sensor_record(machine_id)
    if not latest_sensor:
        raise HTTPException(status_code=404, detail=f"No sensor data found for Machine {machine_id}")
        
    analysis = ml_service.analyze_machine(latest_sensor)
    
    # Format the response as requested
    return {
        "machine_id": machine_id,
        "timestamp": latest_sensor.get("timestamp"),
        "sensors": {
            "temperature_c": latest_sensor.get("temperature_c"),
            "vibration_mm_s": latest_sensor.get("vibration_mm_s"),
            "pressure_bar": latest_sensor.get("pressure_bar"),
            "energy_consumption_kwh": latest_sensor.get("energy_consumption_kwh"),
            "load_percent": latest_sensor.get("load_percent"),
            "production_output_units": latest_sensor.get("production_output_units")
        },
        "analysis": {
            "anomaly": analysis["anomaly"],
            "anomaly_score": analysis["anomaly_score"],
            "failure_within_24h": analysis["failure_within_24h"],
            "failure_probability": analysis["failure_probability"]
        }
    }

@router.get("/{machine_id}/maintenance")
def get_machine_maintenance(machine_id: str):
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
        
    return machine_service.get_machine_maintenance_history(machine_id)

@router.get("/{machine_id}/production")
def get_machine_production(machine_id: str):
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
        
    return machine_service.get_machine_production_history(machine_id)


@router.get("/{machine_id}/sensors")
def get_machine_sensors(machine_id: str, limit: int = 30):
    machine = machine_service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
        
    return machine_service.get_sensor_history(machine_id, limit=limit)
