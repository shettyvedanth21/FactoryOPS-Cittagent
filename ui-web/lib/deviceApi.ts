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
