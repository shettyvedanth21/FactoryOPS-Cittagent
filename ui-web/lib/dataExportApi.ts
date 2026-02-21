import { DATA_EXPORT_SERVICE_BASE } from "./api";

function isJson(res: Response) {
  const ct = res.headers.get("content-type");
  return ct && ct.includes("application/json");
}

export async function runExport(deviceId: string) {
  const res = await fetch(
    `${DATA_EXPORT_SERVICE_BASE}/api/v1/exports/run`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId }),
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Export failed");
  }

  if (isJson(res)) return res.json();
  return {};
}

export async function getExportStatus(deviceId: string) {
  const res = await fetch(
    `${DATA_EXPORT_SERVICE_BASE}/api/v1/exports/status/${deviceId}`
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to get export status");
  }

  if (isJson(res)) return res.json();
  return {};
}