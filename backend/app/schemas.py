from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
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

class WhatIfSimulationRequest(BaseModel):
    machine_id: str = Field(..., description="Target machine identifier (e.g. M_003)")
    timestamp: Optional[str] = Field(None, description="Optional target observation timestamp (e.g. 2023-01-19 22:00:00)")

    @field_validator('machine_id')
    @classmethod
    def validate_machine_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("machine_id is required and cannot be empty")
        return v.strip()


# =====================================================================
# PHASE 4: Human-in-the-Loop Notification & Action Schemas
# =====================================================================

class NotificationItem(BaseModel):
    notification_id: str
    machine_id: str
    timestamp: Optional[str] = None
    severity: str
    title: str
    message: str
    component: str
    root_cause: str
    failure_probability: float
    recommendation: Any
    status: str
    created_at: str
    resolved_at: Optional[str] = None
    rejection_reason: Optional[str] = None

class NotificationListResponse(BaseModel):
    notifications: List[NotificationItem]
    count: int

class AcceptNotificationRequest(BaseModel):
    explicit_approval: bool = Field(..., description="Must be true for human approval")
    approved_by: str = Field(..., description="Operator/engineer audit identifier")
    approved_actions: List[str] = Field(..., description="List of approved software action types")
    notes: Optional[str] = Field(None, description="Optional operator notes")

    @field_validator('approved_by')
    @classmethod
    def validate_approved_by(cls, v: str) -> str:
        stripped = v.strip() if v else ""
        if not stripped:
            raise ValueError("approved_by is required and cannot be empty")
        return stripped

    @field_validator('approved_actions')
    @classmethod
    def validate_approved_actions(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("approved_actions list cannot be empty")
        return [str(a).strip() for a in v if str(a).strip()]

class AcceptNotificationResponse(BaseModel):
    notification_id: str
    status: str
    approved_by: str
    approved_at: str
    actions: List[Dict[str, Any]]
    message: str

class RejectNotificationRequest(BaseModel):
    rejected_by: str = Field(..., description="Operator audit identifier")
    rejection_reason: Optional[str] = Field(None, description="Optional rejection reason")

    @field_validator('rejected_by')
    @classmethod
    def validate_rejected_by(cls, v: str) -> str:
        stripped = v.strip() if v else ""
        if not stripped:
            raise ValueError("rejected_by is required and cannot be empty")
        return stripped

class RejectNotificationResponse(BaseModel):
    notification_id: str
    status: str
    rejected_by: str
    rejected_at: str
    rejection_reason: Optional[str] = None
    message: str

class ActionRecordItem(BaseModel):
    action_id: str
    notification_id: str
    machine_id: str
    action_type: str
    component: str
    priority: str
    reason: str
    status: str
    approved_at: str
    completed_at: str
    result: str
    verification_status: str

class ActionHistoryResponse(BaseModel):
    actions: List[Dict[str, Any]]
    count: int

