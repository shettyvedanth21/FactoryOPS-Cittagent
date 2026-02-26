import { REPORT_SERVICE_BASE } from "./api";

export interface ConsumptionReportParams {
  tenant_id: string;
  device_ids: string[];
  start_date: string;
  end_date: string;
  group_by: "daily" | "weekly";
}

export interface ComparisonReportParams {
  tenant_id: string;
  comparison_type: "machine_vs_machine" | "period_vs_period";
  machine_a_id?: string;
  machine_b_id?: string;
  start_date?: string;
  end_date?: string;
  device_id?: string;
  period_a_start?: string;
  period_a_end?: string;
  period_b_start?: string;
  period_b_end?: string;
}

export interface ReportStatus {
  report_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  error_code?: string;
  error_message?: string;
}

export interface ReportHistoryItem {
  report_id: string;
  status: string;
  report_type: string;
  created_at: string;
  completed_at: string | null;
}

export interface TariffData {
  tenant_id: string;
  energy_rate_per_kwh: number;
  demand_charge_per_kw?: number;
  reactive_penalty_rate?: number;
  fixed_monthly_charge?: number;
  power_factor_threshold?: number;
  currency?: string;
}

export async function submitConsumptionReport(
  params: ConsumptionReportParams
): Promise<{ report_id: string; status: string }> {
  const res = await fetch(`${REPORT_SERVICE_BASE}/energy/consumption`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const errorMsg = errorData.detail || errorData.message || errorData.error || `HTTP ${res.status}`;
    throw new Error(errorMsg);
  }
  return res.json();
}

export async function submitComparisonReport(
  params: ComparisonReportParams
): Promise<{ report_id: string; status: string }> {
  const res = await fetch(`${REPORT_SERVICE_BASE}/energy/comparison`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const errorMsg = errorData.detail || errorData.message || errorData.error || `HTTP ${res.status}`;
    throw new Error(errorMsg);
  }
  return res.json();
}

export async function getReportStatus(
  reportId: string,
  tenantId: string
): Promise<ReportStatus> {
  const res = await fetch(
    `${REPORT_SERVICE_BASE}/${reportId}/status?tenant_id=${encodeURIComponent(tenantId)}`
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function getReportResult(
  reportId: string,
  tenantId: string
): Promise<unknown> {
  const res = await fetch(
    `${REPORT_SERVICE_BASE}/${reportId}/result?tenant_id=${encodeURIComponent(tenantId)}`
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function getReportDownload(
  reportId: string,
  tenantId: string
): Promise<Blob> {
  const res = await fetch(
    `${REPORT_SERVICE_BASE}/${reportId}/download?tenant_id=${encodeURIComponent(tenantId)}`
  );
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`HTTP ${res.status}: ${error}`);
  }
  return res.blob();
}

export async function getReportHistory(
  tenantId: string,
  params?: {
    limit?: number;
    offset?: number;
    report_type?: string;
  }
): Promise<{ reports: ReportHistoryItem[] }> {
  const searchParams = new URLSearchParams({ tenant_id: tenantId });
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());
  if (params?.report_type) searchParams.set("report_type", params.report_type);

  const res = await fetch(`${REPORT_SERVICE_BASE}/history?${searchParams}`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function upsertTariff(data: TariffData): Promise<unknown> {
  const res = await fetch(`${REPORT_SERVICE_BASE}/tariffs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function getTariff(tenantId: string): Promise<TariffData | null> {
  const res = await fetch(`${REPORT_SERVICE_BASE}/tariffs/${encodeURIComponent(tenantId)}`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export interface ScheduleParams {
  report_type: "consumption" | "comparison";
  frequency: "daily" | "weekly" | "monthly";
  params_template: {
    device_ids: string[];
    group_by?: "daily" | "weekly";
  };
}

export interface ScheduleResponse {
  schedule_id: string;
  tenant_id: string;
  report_type: string;
  frequency: string;
  is_active: boolean;
  next_run_at: string | null;
  created_at: string;
}

export interface ScheduleListItem {
  schedule_id: string;
  tenant_id: string;
  report_type: string;
  frequency: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string | null;
  last_result_url: string | null;
  params_template: {
    device_ids: string[];
    group_by?: "daily" | "weekly";
  };
}

export async function createSchedule(
  tenantId: string,
  data: ScheduleParams
): Promise<ScheduleResponse> {
  const res = await fetch(`${REPORT_SERVICE_BASE}/schedules?tenant_id=${encodeURIComponent(tenantId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function getSchedules(tenantId: string): Promise<{ schedules: ScheduleListItem[] }> {
  const res = await fetch(`${REPORT_SERVICE_BASE}/schedules?tenant_id=${encodeURIComponent(tenantId)}`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteSchedule(
  scheduleId: string,
  tenantId: string
): Promise<{ message: string }> {
  const res = await fetch(
    `${REPORT_SERVICE_BASE}/schedules/${scheduleId}?tenant_id=${encodeURIComponent(tenantId)}`,
    { method: "DELETE" }
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}
