import { RULE_ENGINE_SERVICE_BASE } from "./api";

/* ---------- types ---------- */

export type RuleStatus = "active" | "paused" | "archived";
export type RuleScope = "all_devices" | "selected_devices";

export interface Rule {
  ruleId: string;
  ruleName: string;
  description?: string | null;
  scope: RuleScope;
  property: string;
  condition: string;
  threshold: number;
  notificationChannels: string[];
  cooldownMinutes: number;
  deviceIds: string[];
  status: RuleStatus;
  createdAt: string;
}

/* ---------- list ---------- */

export async function listRules(params?: {
  deviceId?: string;
  status?: RuleStatus;
  page?: number;
  pageSize?: number;
}) {
  const query = new URLSearchParams();

  if (params?.deviceId) query.append("device_id", params.deviceId);
  if (params?.status) query.append("status", params.status);

  query.append("page", String(params?.page ?? 1));
  query.append("page_size", String(params?.pageSize ?? 20));

  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/rules?${query.toString()}`
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const json = await res.json();

  return {
    data: json.data.map((r: any) => ({
      ruleId: r.rule_id,
      ruleName: r.rule_name,
      description: r.description,
      scope: r.scope,
      property: r.property,
      condition: r.condition,
      threshold: r.threshold,
      notificationChannels: r.notification_channels,
      cooldownMinutes: r.cooldown_minutes,
      deviceIds: r.device_ids,
      status: r.status,
      createdAt: r.created_at,
    })),
    total: json.total,
  };
}

/* ---------- create ---------- */

export async function createRule(payload: {
  ruleName: string;
  description?: string;
  scope: RuleScope;
  property: string;
  condition: string;
  threshold: number;
  notificationChannels: string[];
  cooldownMinutes: number;
  deviceIds: string[];
}) {
  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/rules`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rule_name: payload.ruleName,
        description: payload.description,
        scope: payload.scope,
        property: payload.property,
        condition: payload.condition,
        threshold: payload.threshold,
        notification_channels: payload.notificationChannels,
        cooldown_minutes: payload.cooldownMinutes,
        device_ids: payload.deviceIds,
      }),
    }
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const json = await res.json();
  return json.data;
}

/* ---------- pause / resume ---------- */

export async function updateRuleStatus(
  ruleId: string,
  status: RuleStatus
) {
  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/rules/${ruleId}/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

/* ---------- delete ---------- */

export async function deleteRule(ruleId: string) {
  const res = await fetch(
    `${RULE_ENGINE_SERVICE_BASE}/api/v1/rules/${ruleId}`,
    { method: "DELETE" }
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}