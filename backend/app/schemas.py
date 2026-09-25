from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime

class MachineSensorInput(BaseModel):
    machine_id: str
    temperature_c: float
    vibration_mm_s: float
    pressure_bar: float
    humidity_percent: float
    energy_consumption_kwh: float
    load_percent: float
    production_output_units: int
    operating_hours: int
    ambient_temperature_c: float

class MachineAnalysisResponse(BaseModel):
    machine_id: str
    anomaly: bool
    anomaly_score: float
    failure_within_24h: bool
    failure_probability: float

class AddMachineRequest(BaseModel):
    machine_name: str
    machine_type: str
    machine_age_years: float = Field(..., ge=0, description="Machine age in years (>= 0)")
    rated_power_kw: float = Field(..., gt=0, description="Rated power in kW (> 0)")
    installation_date: str = Field(..., description="Installation date in YYYY-MM-DD format")
    operating_hours: int = Field(..., ge=0, description="Operating hours (>= 0)")
    maintenance_count: int = Field(..., ge=0, description="Maintenance count (>= 0)")
    criticality_level: str = Field(..., description="Criticality level (Low, Medium, or High)")

    @field_validator('machine_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("machine_name is required and cannot be empty")
        return v.strip()

    @field_validator('machine_type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("machine_type is required and cannot be empty")
        return v.strip()

    @field_validator('installation_date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        stripped = v.strip() if v else ""
        if not stripped:
            raise ValueError("installation_date is required")
        try:
            datetime.strptime(stripped, "%Y-%m-%d")
        except ValueError:
            raise ValueError("installation_date must be a valid date in YYYY-MM-DD format")
        return stripped

    @field_validator('criticality_level')
    @classmethod
    def validate_criticality(cls, v: str) -> str:
        stripped = v.strip().capitalize() if v else ""
        if stripped not in ["Low", "Medium", "High"]:
            raise ValueError("criticality_level must be one of: Low, Medium, High")
        return stripped

class AddMachineResponse(BaseModel):
    success: bool
    machine_id: str
    machine: Dict[str, Any]
    synchronization: Dict[str, Any]
    training: Dict[str, Any]
    message: str
