"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";

import { createRule, updateRuleStatus } from "@/lib/ruleApi";
import { ApiError } from "@/components/ApiError";

const properties = [
  { value: "temperature", label: "Temperature" },
  { value: "voltage", label: "Voltage" },
  { value: "current", label: "Current" },
  { value: "power", label: "Power" },
];

const conditions = [
  { value: ">", label: "Greater than (>)" },
  { value: "<", label: "Less than (<)" },
  { value: "=", label: "Equal to (=)" },
];

const notificationOptions = [
  { value: "email", label: "Email" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "telegram", label: "Telegram" },
];

function CreateRuleContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const deviceIdFromUrl = searchParams.get("device_id") ?? "D1";

  const [ruleName, setRuleName] = useState("");
  const [property, setProperty] = useState("temperature");
  const [condition, setCondition] = useState(">");
  const [threshold, setThreshold] = useState("");
  const [notificationChannels, setNotificationChannels] = useState<string[]>([]);
  const [enabled, setEnabled] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNotificationChange = (channel: string) => {
    setNotificationChannels((prev) =>
      prev.includes(channel)
        ? prev.filter((c) => c !== channel)
        : [...prev, channel]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!ruleName.trim()) {
      setError("Rule name is required");
      return;
    }

    if (threshold === "" || isNaN(Number(threshold))) {
      setError("Threshold must be a valid number");
      return;
    }

    if (notificationChannels.length === 0) {
      setError("At least one notification channel is required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const created = await createRule({
        ruleName: ruleName.trim(),
        scope: "selected_devices",
        property,
        condition,
        threshold: Number(threshold),
        notificationChannels,
        cooldownMinutes: 15,
        deviceIds: [deviceIdFromUrl],
      });

      // 🔴 important fix:
      // backend always creates rule as ACTIVE
      // if user disabled it → immediately pause it
      if (!enabled && created?.rule_id) {
        await updateRuleStatus(created.rule_id, "paused");
      }

      router.push("/rules");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setLoading(false);
    }
  };

  if (error && !loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Create Rule
          </h2>
        </div>
        <ApiError message={error} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Create Rule
        </h2>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow overflow-hidden">
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="space-y-2">
            <label
              htmlFor="ruleName"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              Rule Name
            </label>
            <input
              type="text"
              id="ruleName"
              value={ruleName}
              onChange={(e) => setRuleName(e.target.value)}
              className="w-full rounded-md border border-zinc-300 dark:border-zinc-700
                         bg-white dark:bg-zinc-900
                         px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter rule name"
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="property"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              Property
            </label>
            <select
              id="property"
              value={property}
              onChange={(e) => setProperty(e.target.value)}
              className="w-full rounded-md border border-zinc-300 dark:border-zinc-700
                         bg-white dark:bg-zinc-900
                         px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            >
              {properties.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label
                htmlFor="condition"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                Condition
              </label>
              <select
                id="condition"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                className="w-full rounded-md border border-zinc-300 dark:border-zinc-700
                           bg-white dark:bg-zinc-900
                           px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              >
                {conditions.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="threshold"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                Threshold
              </label>
              <input
                type="number"
                id="threshold"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                className="w-full rounded-md border border-zinc-300 dark:border-zinc-700
                           bg-white dark:bg-zinc-900
                           px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter threshold"
                disabled={loading}
                step="any"
              />
            </div>
          </div>

          <div className="space-y-2">
            <span className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Notification Channels
            </span>

            <div className="space-y-2">
              {notificationOptions.map((option) => (
                <label
                  key={option.value}
                  className="flex items-center space-x-3 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={notificationChannels.includes(option.value)}
                    onChange={() =>
                      handleNotificationChange(option.value)
                    }
                    className="rounded border-zinc-300 dark:border-zinc-700
                               text-blue-600 focus:ring-blue-500"
                    disabled={loading}
                  />
                  <span className="text-sm text-zinc-700 dark:text-zinc-300">
                    {option.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded border-zinc-300 dark:border-zinc-700
                         text-blue-600 focus:ring-blue-500"
              disabled={loading}
            />
            <label
              htmlFor="enabled"
              className="text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              Enable rule
            </label>
          </div>

          <div className="flex items-center gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-700">
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {loading ? "Creating..." : "Create Rule"}
            </button>

            <button
              type="button"
              onClick={() => router.push("/rules")}
              disabled={loading}
              className="px-4 py-2 border border-zinc-300 dark:border-zinc-700
                         text-zinc-700 dark:text-zinc-300 rounded-md text-sm font-medium
                         hover:bg-zinc-50 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CreateRulePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CreateRuleContent />
    </Suspense>
  );
}