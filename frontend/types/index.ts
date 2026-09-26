export interface Machine {
  machine_id: string;
  machine_name: string;
  machine_type: string;
  machine_age_years: number;
  rated_power_kw: number;
  installation_date: string;
  operating_hours: number;
  maintenance_count: number;
  criticality_level: "Low" | "Medium" | "High" | string;
}

export interface SensorData {
  timestamp?: string;
  machine_id?: string;
  temperature_c: number;
  vibration_mm_s: number;
  pressure_bar: number;
  humidity_percent?: number;
  energy_consumption_kwh: number;
  load_percent: number;
  production_output_units: number;
  ambient_temperature_c?: number;
}

export interface MachineAnalysis {
  machine_id: string;
  timestamp: string;
  sensors: SensorData;
  analysis: {
    anomaly: boolean;
    anomaly_score: number;
    failure_within_24h: number;
    failure_probability: number;
  };
}

export interface MaintenanceRecord {
  maintenance_id: string;
  machine_id: string;
  maintenance_date: string;
  maintenance_type: string;
  component: string;
  description: string;
  downtime_hours: number;
  maintenance_cost: number;
  technician_notes: string;
}

export interface ProductionRecord {
  timestamp: string;
  machine_id: string;
  production_target: number;
  production_output: number;
  rejected_units: number;
  downtime_minutes: number;
  efficiency_percent: number;
}

export interface Recommendation {
  action: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  details: string;
  estimated_cost_impact?: string;
  recommended_actions?: string[];
}

export interface LLMStatus {
  enabled: boolean;
  provider: string;
  model: string;
  fallback_model: string;
  loaded: boolean;
  loaded_model?: string | null;
  device?: string;
  latency_ms?: number;
  status_message?: string;
  hardware?: {
    total_ram_gb?: number;
    available_ram_gb?: number;
    cuda_available?: boolean;
    gpu_name?: string | null;
    vram_gb?: number;
  };
}

export interface AgentAnalysis {
  machine_id: string;
  timestamp?: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | string;
  failure_probability: number;
  anomaly: boolean;
  root_cause?: string | null;
  confidence?: number | null;
  candidate_scores?: Record<string, number> | null;
  evidence: string[];
  impact: {
    production_impact?: string;
    energy_impact?: string;
    downtime_risk?: string;
    urgency?: string;
  };
  recommendations: Recommendation[];
  agent_trace: string[];
  final_report: string;
  llm_status?: LLMStatus | null;
  investigation_explanation?: string | null;
  rca_explanation?: string | null;
  decision_explanation?: string | null;
  notification_id?: string | null;
  approval_status?: "NOT_REQUIRED" | "PENDING" | "APPROVED" | "REJECTED" | string | null;
  verification_status?: "NOT_STARTED" | "PENDING_TELEMETRY" | "VERIFIED" | "FAILED" | string | null;
}

export interface NotificationItem {
  notification_id: string;
  machine_id: string;
  timestamp?: string | null;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  title: string;
  message: string;
  component: string;
  root_cause: string;
  failure_probability: number;
  recommendation: string[] | string;
  status: "PENDING" | "ACTION_IN_PROGRESS" | "VERIFICATION_PENDING" | "COMPLETED" | "FAILED" | "REJECTED" | string;
  created_at: string;
  resolved_at?: string | null;
  rejection_reason?: string | null;
}

export interface NotificationListResponse {
  notifications: NotificationItem[];
  count: number;
}

export interface AcceptNotificationRequest {
  explicit_approval: boolean;
  approved_by: string;
  approved_actions: string[];
  notes?: string;
}

export interface ActionResultItem {
  action_type: string;
  action_id?: string;
  status: "VERIFICATION_PENDING" | "SIMULATED" | "COMPLETED" | "FAILED" | "BLOCKED" | string;
  details?: Record<string, unknown>;
  error?: string;
}

export interface AcceptNotificationResponse {
  notification_id: string;
  status: string;
  approved_by: string;
  approved_at: string;
  actions: ActionResultItem[];
  message: string;
}

export interface RejectNotificationRequest {
  rejected_by: string;
  rejection_reason?: string;
}

export interface RejectNotificationResponse {
  notification_id: string;
  status: string;
  rejected_by: string;
  rejected_at: string;
  rejection_reason?: string | null;
  message: string;
}

export interface ActionRecord {
  action_id: string;
  notification_id: string;
  machine_id: string;
  action_type: string;
  component: string;
  priority: string;
  reason: string;
  status: "VERIFICATION_PENDING" | "SIMULATED" | "COMPLETED" | "FAILED" | "BLOCKED" | string;
  approved_at: string;
  completed_at: string;
  result: string;
  verification_status: string;
}

export interface ActionHistoryResponse {
  actions: ActionRecord[];
  count: number;
}


export interface MachineWithStatus {
  metadata: Machine;
  latest_sensor?: SensorData;
  analysis?: {
    anomaly: boolean;
    failure_probability: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN" | string;
  };
}

export interface NewMachineInput {
  machine_name: string;
  machine_type: string;
  machine_age_years: number;
  rated_power_kw: number;
  installation_date: string;
  operating_hours: number;
  maintenance_count: number;
  criticality_level: "Low" | "Medium" | "High";
}

export interface AddMachineResponse {
  success: boolean;
  machine_id: string;
  machine: Machine;
  synchronization: {
    success: boolean;
    message: string;
  };
  training: {
    success: boolean;
    message: string;
  };
  message: string;
}

export interface SimulationTrajectoryPoint {
  hour: number;
  projected_risk_index: number;
  projected_temperature: number;
  projected_vibration: number;
  projected_energy: number;
  projected_production: number;
  projected_pressure: number;
}

export interface ScenarioProjection {
  projected_risk_index: number;
  production_loss_units: number;
  energy_wastage_kwh: number;
  downtime_exposure_hours: number;
  hours_above_warning: number;
  hours_above_critical: number;
  trajectory: SimulationTrajectoryPoint[];
}

export interface WhatIfSimulationResponse {
  machine_id: string;
  timestamp: string;
  root_cause: string;
  current_state: {
    risk_level: "LOW" | "MEDIUM" | "HIGH" | string;
    failure_probability: number;
    production: number;
    energy: number;
    temperature_c?: number;
    vibration_mm_s?: number;
    pressure_bar?: number;
    anomaly: boolean;
    downtime_risk: string;
  };
  assumptions: {
    root_cause_profile: string;
    intervention_action: string;
    load_reduction: string;
    trend_damping: string;
    energy_recovery: string;
    production_stabilization: string;
    baseline_reference: string;
    horizon_hours: number;
    disclaimer: string;
  };
  intervene_now: ScenarioProjection;
  do_nothing: ScenarioProjection;
  estimated_difference: {
    production_loss_avoided: number;
    energy_wastage_avoided: number;
    downtime_exposure_avoided: number;
  };
  explanation?: string;
}



