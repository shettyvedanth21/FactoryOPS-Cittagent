import { DEVICE_SERVICE_BASE } from "./api";

/**
 * Raw backend shape
 */
interface BackendDevice {
  device_id: string;
  device_name: string;
  device_type: string;
  status: string;
  location: string | null;
}

/**
 * UI shape
 */
export interface Device {
  id: string;
  name: string;
  type: string;
  status: string;
  location: string;
}

interface DeviceApiResponse<T> {
  success: boolean;
  data: T;
}

/* ----------------------- */
/* Mapping (single place) */
/* ----------------------- */

function mapDevice(d: BackendDevice): Device {
  return {
    id: d.device_id,
    name: d.device_name,
    type: d.device_type,
    status: d.status,
    location: d.location ?? "",
  };
}

/* ----------------------- */

export async function getDevices(): Promise<Device[]> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const json: DeviceApiResponse<BackendDevice[]> = await res.json();

  return (json.data || []).map(mapDevice);
}

export async function getDeviceById(deviceId: string): Promise<Device | null> {
  if (!deviceId) return null;

  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}`
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const json: DeviceApiResponse<BackendDevice> = await res.json();

  return json.data ? mapDevice(json.data) : null;
}


/* =====================================================
 * Shift Configuration API
 * ===================================================== */

export interface Shift {
  id: number;
  device_id: string;
  shift_name: string;
  shift_start: string;  // HH:MM format
  shift_end: string;    // HH:MM format
  maintenance_break_minutes: number;
  day_of_week: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ShiftCreate {
  shift_name: string;
  shift_start: string;
  shift_end: string;
  maintenance_break_minutes: number;
  day_of_week?: number | null;
  is_active?: boolean;
}

export interface UptimeData {
  device_id: string;
  uptime_percentage: number | null;
  total_planned_minutes: number;
  total_effective_minutes: number;
  shifts_configured: number;
  message: string;
}

function mapShift(s: any): Shift {
  return {
    id: s.id,
    device_id: s.device_id,
    shift_name: s.shift_name,
    shift_start: s.shift_start,
    shift_end: s.shift_end,
    maintenance_break_minutes: s.maintenance_break_minutes,
    day_of_week: s.day_of_week,
    is_active: s.is_active,
    created_at: s.created_at,
    updated_at: s.updated_at,
  };
}

export async function getShifts(deviceId: string): Promise<Shift[]> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/shifts`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return (json.data || []).map(mapShift);
}

export async function createShift(deviceId: string, shift: ShiftCreate): Promise<Shift> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/shifts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(shift),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return mapShift(json.data);
}

export async function updateShift(
  deviceId: string,
  shiftId: number,
  shift: Partial<ShiftCreate>
): Promise<Shift> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/shifts/${shiftId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(shift),
    }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return mapShift(json.data);
}

export async function deleteShift(deviceId: string, shiftId: number): Promise<void> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/shifts/${shiftId}`,
    { method: "DELETE" }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export async function getUptime(deviceId: string): Promise<UptimeData> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/uptime`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}


/* =====================================================
 * Health Configuration API
 * ===================================================== */

export interface HealthConfig {
  id: number;
  device_id: string;
  parameter_name: string;
  normal_min: number | null;
  normal_max: number | null;
  max_min: number | null;
  max_max: number | null;
  weight: number;
  ignore_zero_value: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HealthConfigCreate {
  parameter_name: string;
  normal_min?: number | null;
  normal_max?: number | null;
  max_min?: number | null;
  max_max?: number | null;
  weight: number;
  ignore_zero_value?: boolean;
  is_active?: boolean;
}

export interface WeightValidation {
  is_valid: boolean;
  total_weight: number;
  message: string;
  parameters: Array<{
    parameter_name: string;
    weight: number;
    is_active: boolean;
  }>;
}

export interface ParameterScore {
  parameter_name: string;
  value: number;
  raw_score: number;
  weighted_score: number;
  weight: number;
  status: string;
  status_color: string;
}

export interface HealthScore {
  device_id: string;
  health_score: number | null;
  status: string;
  status_color: string;
  message: string;
  machine_state: string;
  parameter_scores: ParameterScore[];
  total_weight_configured: number;
  parameters_included: number;
  parameters_skipped: number;
}

export interface TelemetryValues {
  values: Record<string, number>;
  machine_state?: string;
}

function mapHealthConfig(c: any): HealthConfig {
  return {
    id: c.id,
    device_id: c.device_id,
    parameter_name: c.parameter_name,
    normal_min: c.normal_min,
    normal_max: c.normal_max,
    max_min: c.max_min,
    max_max: c.max_max,
    weight: c.weight,
    ignore_zero_value: c.ignore_zero_value,
    is_active: c.is_active,
    created_at: c.created_at,
    updated_at: c.updated_at,
  };
}

export async function getHealthConfigs(deviceId: string): Promise<HealthConfig[]> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-config`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return (json.data || []).map(mapHealthConfig);
}

export async function createHealthConfig(
  deviceId: string,
  config: HealthConfigCreate
): Promise<HealthConfig> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-config`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return mapHealthConfig(json.data);
}

export async function updateHealthConfig(
  deviceId: string,
  configId: number,
  config: Partial<HealthConfigCreate>
): Promise<HealthConfig> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-config/${configId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return mapHealthConfig(json.data);
}

export async function deleteHealthConfig(
  deviceId: string,
  configId: number
): Promise<void> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-config/${configId}`,
    { method: "DELETE" }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export async function validateHealthWeights(
  deviceId: string
): Promise<WeightValidation> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-config/validate-weights`
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function bulkCreateHealthConfigs(
  deviceId: string,
  configs: HealthConfigCreate[]
): Promise<HealthConfig[]> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-config/bulk`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(configs),
    }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const json = await res.json();
  return (json.data || []).map(mapHealthConfig);
}

export async function calculateHealthScore(
  deviceId: string,
  telemetry: TelemetryValues
): Promise<HealthScore> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/health-score`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(telemetry),
    }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}
