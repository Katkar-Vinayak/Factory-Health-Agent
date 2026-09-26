import {
  Machine,
  SensorData,
  MachineAnalysis,
  MaintenanceRecord,
  ProductionRecord,
  AgentAnalysis,
  NotificationItem,
  NotificationListResponse,
  AcceptNotificationRequest,
  AcceptNotificationResponse,
  RejectNotificationRequest,
  RejectNotificationResponse,
  ActionHistoryResponse
} from "../types";

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    if (typeof window !== "undefined") {
      const currentHost = window.location.hostname;
      if (currentHost === "localhost") {
        return "http://localhost:8000";
      }
      if (currentHost === "127.0.0.1") {
        return "http://127.0.0.1:8000";
      }
    }
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

async function fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${getApiBaseUrl()}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(url, {
      cache: "no-store",
      credentials: "include",
      signal: options?.signal || controller.signal,
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        ...(options?.headers || {})
      }
    });
    clearTimeout(timeoutId);

    if (res.status === 401) {
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        window.location.href = "/login";
      }
    }

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.detail) errorDetail = errorJson.detail;
      } catch {
        if (errorText) errorDetail = errorText;
      }
      throw new Error(errorDetail);
    }

    return await res.json();
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof Error) {
      if (err.name === "AbortError") {
        throw new Error(`Request to backend server timed out after 15 seconds. Ensure FastAPI is running on port 8000.`);
      }
      if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
        throw new Error(`Unable to connect to backend server at ${getApiBaseUrl() || "port 8000"}. Ensure FastAPI is running on port 8000.`);
      }
      throw err;
    }
    throw new Error("Unknown error while communicating with backend.");
  }
}

export async function getMachines(): Promise<Machine[]> {
  return fetchJSON<Machine[]>(`/api/machines?_t=${Date.now()}`);
}

export async function getMachine(
  machineId: string
): Promise<{ metadata: Machine; latest_sensor: SensorData }> {
  return fetchJSON<{ metadata: Machine; latest_sensor: SensorData }>(
    `/api/machines/${encodeURIComponent(machineId)}`
  );
}

export async function getMachineAnalysis(machineId: string): Promise<MachineAnalysis> {
  return fetchJSON<MachineAnalysis>(
    `/api/machines/${encodeURIComponent(machineId)}/analysis`
  );
}

export async function getMaintenanceHistory(
  machineId: string
): Promise<MaintenanceRecord[]> {
  return fetchJSON<MaintenanceRecord[]>(
    `/api/machines/${encodeURIComponent(machineId)}/maintenance`
  );
}

export async function getProductionHistory(
  machineId: string
): Promise<ProductionRecord[]> {
  return fetchJSON<ProductionRecord[]>(
    `/api/machines/${encodeURIComponent(machineId)}/production`
  );
}

export async function getSensorHistory(
  machineId: string,
  limit: number = 30
): Promise<SensorData[]> {
  return fetchJSON<SensorData[]>(
    `/api/machines/${encodeURIComponent(machineId)}/sensors?limit=${limit}`
  );
}

export async function analyzeMachine(
  machineId: string,
  timestamp?: string
): Promise<AgentAnalysis> {
  return fetchJSON<AgentAnalysis>("/api/agent/analyze", {
    method: "POST",
    body: JSON.stringify({
      machine_id: machineId,
      timestamp: timestamp || undefined
    })
  });
}

export async function addMachine(
  machineData: import("../types").NewMachineInput
): Promise<import("../types").AddMachineResponse> {
  return fetchJSON<import("../types").AddMachineResponse>("/api/machines/add", {
    method: "POST",
    body: JSON.stringify(machineData)
  });
}

export async function simulateWhatIf(
  machineId: string,
  timestamp?: string
): Promise<import("../types").WhatIfSimulationResponse> {
  return fetchJSON<import("../types").WhatIfSimulationResponse>("/api/simulation/what-if", {
    method: "POST",
    body: JSON.stringify({
      machine_id: machineId,
      ...(timestamp ? { timestamp } : {})
    })
  });
}

export async function getModelStatus(): Promise<import("../types").LLMStatus> {
  return fetchJSON<import("../types").LLMStatus>("/api/agent/model-status");
}

export async function getNotifications(params?: {
  status?: string;
  machine_id?: string;
  severity?: string;
}): Promise<NotificationListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.machine_id) query.set("machine_id", params.machine_id);
  if (params?.severity) query.set("severity", params.severity);
  query.set("_t", Date.now().toString());

  const qs = query.toString();
  return fetchJSON<NotificationListResponse>(`/api/notifications${qs ? `?${qs}` : ""}`);
}

export async function getNotification(notificationId: string): Promise<NotificationItem> {
  return fetchJSON<NotificationItem>(`/api/notifications/${encodeURIComponent(notificationId)}?_t=${Date.now()}`);
}

export async function acceptNotification(
  notificationId: string,
  payload: AcceptNotificationRequest
): Promise<AcceptNotificationResponse> {
  return fetchJSON<AcceptNotificationResponse>(
    `/api/notifications/${encodeURIComponent(notificationId)}/accept`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function rejectNotification(
  notificationId: string,
  payload: RejectNotificationRequest
): Promise<RejectNotificationResponse> {
  return fetchJSON<RejectNotificationResponse>(
    `/api/notifications/${encodeURIComponent(notificationId)}/reject`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getActionHistory(params?: {
  machine_id?: string;
  notification_id?: string;
  status?: string;
  action_type?: string;
}): Promise<ActionHistoryResponse> {
  const query = new URLSearchParams();
  if (params?.machine_id) query.set("machine_id", params.machine_id);
  if (params?.notification_id) query.set("notification_id", params.notification_id);
  if (params?.status) query.set("status", params.status);
  if (params?.action_type) query.set("action_type", params.action_type);
  query.set("_t", Date.now().toString());

  const qs = query.toString();
  return fetchJSON<ActionHistoryResponse>(`/api/notifications/actions/history${qs ? `?${qs}` : ""}`);
}



