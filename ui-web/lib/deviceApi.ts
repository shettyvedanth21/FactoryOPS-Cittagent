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
