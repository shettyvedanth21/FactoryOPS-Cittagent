import { DATA_SERVICE_BASE, RULE_ENGINE_SERVICE_BASE, DEVICE_SERVICE_BASE } from "./api";

/* ---------- telemetry ---------- */

export interface TelemetryPoint {
  timestamp: string;
  [key: string]: number | string | undefined;
}

export async function getTelemetry(
  deviceId: string,
  params?: Record<string, string>
): Promise<TelemetryPoint[]> {

  const query = new URLSearchParams(params || {}).toString();

  const url =
    `${DATA_SERVICE_BASE}/api/v1/data/telemetry/${deviceId}` +
    (query ? `?${query}` : "");

  const res = await fetch(url);

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  const json = await res.json();

  // ✅ Permanent, shape-safe normalization

  // New API shape:
  // { success, data: { items: [...] } }
  if (json?.data?.items && Array.isArray(json.data.items)) {
    return json.data.items;
  }

  // Older / alternate shapes
  if (Array.isArray(json?.data)) {
    return json.data;
  }

  if (Array.isArray(json)) {
    return json;
  }

  return [];
}


/* ---------- stats ---------- */

export interface DeviceStats {
  device_id: string;
  [key: string]: number | string;
}

export async function getDeviceStats(deviceId: string): Promise<DeviceStats> {

  const res = await fetch(
    `${DATA_SERVICE_BASE}/api/v1/data/stats/${deviceId}`
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  const json = await res.json();

  return json.data ?? json;
}


export async function getDeviceFields(deviceId: string): Promise<string[]> {
  try {
    const telemetry = await getTelemetry(deviceId, { limit: "1" });
    if (telemetry.length === 0) return [];
    
    const latest = telemetry[0];
    const fields: string[] = [];
    
    for (const [key, value] of Object.entries(latest)) {
      if (key !== 'timestamp' && key !== 'device_id' && key !== 'schema_version' && 
          key !== 'enrichment_status' && key !== 'table' && typeof value === 'number') {
        fields.push(key);
      }
    }
    
    return fields;
  } catch {
    return [];
  }
}


/* ---------- alerts (rule-engine-service) ---------- */

export interface Alert {
  alertId: string;
  ruleId: string;
  deviceId: string;
  severity: string;
  message: string;
  actualValue: number;
  thresholdValue: number;
  status: string;
  acknowledgedBy: string | null;
  acknowledgedAt: string | null;
  resolvedAt: string | null;
  createdAt: string;
}

export async function getDeviceAlerts(
  deviceId: string,
  params?: {
    page?: number;
    pageSize?: number;
    status?: string;
  }
): Promise<{
  data: Alert[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}> {

  const query = new URLSearchParams({
    device_id: deviceId,
    page: String(params?.page ?? 1),
    page_size: String(params?.pageSize ?? 20),
  });

  if (params?.status) {
    query.append("status", params.status);
  }

  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/alerts?${query.toString()}`
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  const json = await res.json();

  return {
    data: json.data.map((a: any) => ({
      alertId: a.alert_id,
      ruleId: a.rule_id,
      deviceId: a.device_id,
      severity: a.severity,
      message: a.message,
      actualValue: a.actual_value,
      thresholdValue: a.threshold_value,
      status: a.status,
      acknowledgedBy: a.acknowledged_by,
      acknowledgedAt: a.acknowledged_at,
      resolvedAt: a.resolved_at,
      createdAt: a.created_at,
    })),
    total: json.total,
    page: json.page,
    pageSize: json.page_size,
    totalPages: json.total_pages,
  };
}


/* ---------- alert actions ---------- */

export async function acknowledgeAlert(
  alertId: string,
  acknowledgedBy: string
) {
  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/alerts/${alertId}/acknowledge`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        acknowledged_by: acknowledgedBy,
      }),
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  return res.json();
}

export async function resolveAlert(alertId: string) {
  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/alerts/${alertId}/resolve`,
    {
      method: "PATCH",
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }

  return res.json();
}


export async function getAllDevicesProperties(): Promise<{
  devices: Record<string, string[]>;
  all_properties: string[];
}> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices/properties`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }
  return res.json();
}


export async function getCommonProperties(deviceIds: string[]): Promise<{
  properties: string[];
  device_count: number;
  message: string;
}> {
  const res = await fetch(
    `${DEVICE_SERVICE_BASE}/api/v1/devices/properties/common`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_ids: deviceIds }),
    }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }
  return res.json();
}


export async function getDeviceProperties(deviceId: string): Promise<string[]> {
  const res = await fetch(`${DEVICE_SERVICE_BASE}/api/v1/devices/${deviceId}/properties?numeric_only=true`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} - ${text}`);
  }
  const data = await res.json();
  return data.map((p: { property_name: string }) => p.property_name);
}