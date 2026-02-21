"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { getDeviceById, Device } from "@/lib/deviceApi";
import {
  getTelemetry,
  getDeviceStats,
  TelemetryPoint,
  DeviceStats,
} from "@/lib/dataApi";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TimeSeriesChart } from "@/components/charts/telemetry-charts";
import { RealTimeGauge } from "@/components/charts/Gauge";
import { MachineRulesView } from "@/app/machines/[deviceId]/rules/machine-rules-view";

const METRIC_LABELS: Record<string, string> = {
  power: "Power",
  voltage: "Voltage",
  current: "Current",
  temperature: "Temperature",
  pressure: "Pressure",
  humidity: "Humidity",
  vibration: "Vibration",
  frequency: "Frequency",
  power_factor: "Power Factor",
  speed: "Speed",
  torque: "Torque",
  oil_pressure: "Oil Pressure",
};

const METRIC_UNITS: Record<string, string> = {
  power: " W",
  voltage: " V",
  current: " A",
  temperature: " °C",
  pressure: " bar",
  humidity: " %",
  vibration: " mm/s",
  frequency: " Hz",
  power_factor: "",
  speed: " RPM",
  torque: " Nm",
  oil_pressure: " bar",
};

const METRIC_COLORS: Record<string, string> = {
  power: "#2563eb",
  voltage: "#d97706",
  current: "#7c3aed",
  temperature: "#dc2626",
  pressure: "#059669",
  humidity: "#0891b2",
  vibration: "#ea580c",
  frequency: "#4f46e5",
  power_factor: "#8b5cf6",
  speed: "#0d9488",
  torque: "#be185d",
  oil_pressure: "#65a30d",
};

const METRIC_RANGES: Record<string, [number, number]> = {
  power: [0, 500],
  voltage: [200, 250],
  current: [0, 20],
  temperature: [0, 120],
  pressure: [0, 10],
  humidity: [0, 100],
  vibration: [0, 10],
  frequency: [45, 55],
  power_factor: [0.8, 1.0],
  speed: [1000, 2000],
  torque: [0, 500],
  oil_pressure: [0, 5],
};

function getDynamicMetrics(telemetry: TelemetryPoint[]): string[] {
  const latest = telemetry.at(-1);
  if (!latest) return [];
  
  const metrics = new Set<string>();
  for (const [key, value] of Object.entries(latest)) {
    if (key !== 'timestamp' && key !== 'device_id' && key !== 'schema_version' && 
        key !== 'enrichment_status' && key !== 'table' && typeof value === 'number') {
      metrics.add(key);
    }
  }
  return Array.from(metrics);
}

function getMetricData(telemetry: TelemetryPoint[], metric: string) {
  return telemetry
    .filter((t) => typeof (t as any)[metric] === "number")
    .map((t) => ({
      timestamp: t.timestamp,
      value: (t as any)[metric] as number,
    }));
}

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return timestamp;
    }
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch {
    return timestamp;
  }
}

export default function MachineDashboardPage() {
  const params = useParams();
  const deviceId = (params.deviceId as string) || "";

  const [machine, setMachine] = useState<Device | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryPoint[]>([]);
  const [stats, setStats] = useState<DeviceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "telemetry" | "rules"
  >("overview");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);

  const fetchData = async (isInitial = false) => {
    try {
      const [machineData, telemetryData, statsData] = await Promise.all([
        getDeviceById(deviceId),
        getTelemetry(deviceId, { limit: "100" }),
        getDeviceStats(deviceId),
      ]);

      if (isInitial) {
        setMachine(machineData);
      }
      setTelemetry(telemetryData);
      setStats(statsData);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      if (isInitial) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch machine data"
        );
      }
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (!deviceId) return;

    fetchData(true);

    pollingInterval.current = setInterval(() => {
      fetchData(false);
    }, 1000);

    return () => {
      if (pollingInterval.current) {
        clearInterval(pollingInterval.current);
      }
    };
  }, [deviceId]);

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-slate-600">Loading machine data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !machine) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 font-semibold mb-2">
            Error loading machine
          </h2>
          <p className="text-red-600">{error || "Machine not found"}</p>
          <Link href="/machines">
            <Button variant="outline" className="mt-4">
              Back to Machines
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const latestTelemetry = telemetry.at(-1);
  const dynamicMetrics = getDynamicMetrics(telemetry);

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
            <Link href="/machines" className="hover:text-slate-900">
              Machines
            </Link>
            <span>/</span>
            <span className="text-slate-900">{machine.name}</span>
          </div>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                {machine.name}
              </h1>
              <p className="text-slate-500 font-mono mt-1">{machine.id}</p>
            </div>
            <StatusBadge status={machine.status} />
          </div>
          
          {lastUpdated && (
            <p className="text-xs text-slate-400 mt-2">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 mb-6">
          <nav className="flex gap-8">
            {[
              { id: "overview", label: "Overview" },
              { id: "telemetry", label: "Telemetry" },
              { id: "rules", label: "Configure Rules" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() =>
                  setActiveTab(tab.id as "overview" | "telemetry" | "rules")
                }
                className={`pb-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* ---------------- OVERVIEW ---------------- */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Machine Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div>
                    <p className="text-sm text-slate-500">Name</p>
                    <p className="text-sm font-medium mt-1">
                      {machine.name}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">ID</p>
                    <p className="text-sm font-mono mt-1">
                      {machine.id}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Type</p>
                    <p className="text-sm font-medium mt-1 capitalize">
                      {machine.type}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Location</p>
                    <p className="text-sm font-medium mt-1">
                      {machine.location || "—"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Dynamic Real-Time Gauges */}
            {dynamicMetrics.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {dynamicMetrics.map((metric) => {
                  const value = (latestTelemetry as any)[metric];
                  if (typeof value !== 'number') return null;
                  
                  const range = METRIC_RANGES[metric] || [0, 100];
                  const unit = METRIC_UNITS[metric] || "";
                  const color = METRIC_COLORS[metric] || "#2563eb";
                  
                  return (
                    <RealTimeGauge
                      key={metric}
                      value={value}
                      label={METRIC_LABELS[metric] || metric}
                      unit={unit}
                      min={range[0]}
                      max={range[1]}
                      color={color}
                    />
                  );
                })}
              </div>
            )}

            {/* Dynamic Charts */}
            {telemetry.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {dynamicMetrics.map((metric) => {
                  const data = getMetricData(telemetry, metric);
                  if (data.length === 0) return null;
                  
                  return (
                    <Card key={metric}>
                      <CardHeader>
                        <CardTitle>
                          {METRIC_LABELS[metric] || metric} Trend
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <TimeSeriesChart
                          data={data}
                          color={METRIC_COLORS[metric] || "#2563eb"}
                          unit={METRIC_UNITS[metric] || ""}
                        />
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ---------------- TELEMETRY ---------------- */}
        {activeTab === "telemetry" && (
          <div className="space-y-6">
            {telemetry.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-slate-500">
                    No telemetry data available
                  </p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Recent Telemetry</CardTitle>
                  <span className="text-xs text-slate-400">
                    Auto-refresh every 3s • {telemetry.length} records
                  </span>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                            Timestamp
                          </th>
                          {dynamicMetrics.map((metric) => (
                            <th key={metric} className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                              {METRIC_LABELS[metric] || metric}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-slate-200">
                        {telemetry
                          .slice()
                          .reverse()
                          .slice(0, 20)
                          .map((point, i) => (
                            <tr key={i} className={i === 0 ? "bg-blue-50" : ""}>
                              <td className="px-6 py-3 text-sm font-mono">
                                {formatTimestamp(point.timestamp)}
                              </td>
                              {dynamicMetrics.map((metric) => {
                                const value = (point as any)[metric];
                                return (
                                  <td key={metric} className="px-6 py-3 text-sm">
                                    {typeof value === "number"
                                      ? value.toFixed(2)
                                      : "—"}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* ---------------- RULES ---------------- */}
        {activeTab === "rules" && (
          <MachineRulesView deviceId={deviceId} />
        )}
      </div>
    </div>
  );
}
