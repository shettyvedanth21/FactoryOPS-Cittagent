"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { getDeviceById, Device, getShifts, createShift, deleteShift, Shift, ShiftCreate, getUptime, UptimeData } from "@/lib/deviceApi";
import { getTelemetry, TelemetryPoint } from "@/lib/dataApi";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RealTimeGauge } from "@/components/charts/Gauge";
import { TimeSeriesChart } from "@/components/charts/telemetry-charts";
import { MachineRulesView } from "@/app/machines/[deviceId]/rules/machine-rules-view";

const METRIC_LABELS: Record<string, string> = {
  power: "Power", voltage: "Voltage", current: "Current", temperature: "Temperature",
  pressure: "Pressure", humidity: "Humidity", vibration: "Vibration", frequency: "Frequency",
  power_factor: "Power Factor", speed: "Speed", torque: "Torque", oil_pressure: "Oil Pressure",
};

const METRIC_UNITS: Record<string, string> = {
  power: " W", voltage: " V", current: " A", temperature: " °C",
  pressure: " bar", humidity: " %", vibration: " mm/s", frequency: " Hz",
  power_factor: "", speed: " RPM", torque: " Nm", oil_pressure: " bar",
};

const METRIC_COLORS: Record<string, string> = {
  power: "#2563eb", voltage: "#d97706", current: "#7c3aed", temperature: "#dc2626",
  pressure: "#059669", humidity: "#0891b2", vibration: "#ea580c", frequency: "#4f46e5",
  power_factor: "#8b5cf6", speed: "#0d9488", torque: "#be185d", oil_pressure: "#65a30d",
};

const METRIC_RANGES: Record<string, [number, number]> = {
  power: [0, 500], voltage: [200, 250], current: [0, 20], temperature: [0, 120],
  pressure: [0, 10], humidity: [0, 100], vibration: [0, 10], frequency: [45, 55],
  power_factor: [0.8, 1.0], speed: [1000, 2000], torque: [0, 500], oil_pressure: [0, 5],
};

const DAYS_OF_WEEK = [
  { value: null, label: "All Days" },
  { value: 0, label: "Monday" }, { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" }, { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" }, { value: 5, label: "Saturday" }, { value: 6, label: "Sunday" },
];

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
  return telemetry.filter((t) => typeof (t as any)[metric] === "number")
    .map((t) => ({ timestamp: t.timestamp, value: (t as any)[metric] as number }));
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    if (isNaN(date.getTime())) return ts;
    return date.toLocaleString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  } catch { return ts; }
}

function UptimeCircle({ uptime, onClick }: { uptime: UptimeData | null; onClick: () => void }) {
  const percentage = uptime?.uptime_percentage ?? 0;
  const color = percentage >= 95 ? "#22c55e" : percentage >= 80 ? "#eab308" : "#ef4444";
  
  return (
    <div className="relative cursor-pointer group" onClick={onClick}>
      <div className="w-16 h-16">
        <svg className="w-full h-full transform -rotate-90">
          <circle cx="32" cy="32" r="28" stroke="#e2e8f0" strokeWidth="6" fill="none" />
          <circle cx="32" cy="32" r="28" stroke={color} strokeWidth="6" fill="none"
            strokeDasharray={`${(percentage / 100) * 176} 176`} className="transition-all duration-500" />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold">{percentage.toFixed(0)}%</span>
        </div>
      </div>
      
      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 w-48 bg-white shadow-lg rounded-lg border p-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
        <p className="text-xs font-semibold text-slate-700 mb-2">Uptime Details</p>
        {uptime ? (
          <>
            <p className="text-xs text-slate-600">Active Shifts: <span className="font-medium">{uptime.shifts_configured}</span></p>
            <p className="text-xs text-slate-600">Planned: <span className="font-medium">{Math.floor(uptime.total_planned_minutes / 60)}h {uptime.total_planned_minutes % 60}m</span></p>
            <p className="text-xs text-slate-600">Effective: <span className="font-medium">{Math.floor(uptime.total_effective_minutes / 60)}h {uptime.total_effective_minutes % 60}m</span></p>
          </>
        ) : (
          <p className="text-xs text-slate-500">No shifts configured</p>
        )}
      </div>
    </div>
  );
}

export default function MachineDashboardPage() {
  const params = useParams();
  const deviceId = (params.deviceId as string) || "";

  const [machine, setMachine] = useState<Device | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryPoint[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [uptime, setUptime] = useState<UptimeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "telemetry" | "parameters" | "rules">("overview");
  const [showAddShift, setShowAddShift] = useState(false);
  const [newShift, setNewShift] = useState<ShiftCreate>({
    shift_name: "", shift_start: "09:00", shift_end: "17:00", maintenance_break_minutes: 0, day_of_week: null, is_active: true,
  });
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);

  const fetchData = async (isInitial = false) => {
    try {
      const [machineData, telemetryData, uptimeData, shiftsData] = await Promise.all([
        getDeviceById(deviceId),
        getTelemetry(deviceId, { limit: "100" }),
        getUptime(deviceId),
        getShifts(deviceId),
      ]);
      if (isInitial) setMachine(machineData);
      setTelemetry(telemetryData);
      setUptime(uptimeData);
      setShifts(shiftsData);
      setError(null);
    } catch (err) {
      if (isInitial) setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    if (!deviceId) return;
    fetchData(true);
    pollingInterval.current = setInterval(() => fetchData(false), 1000);
    return () => { if (pollingInterval.current) clearInterval(pollingInterval.current); };
  }, [deviceId]);

  const handleAddShift = async () => {
    try {
      await createShift(deviceId, newShift);
      setShowAddShift(false);
      setNewShift({ shift_name: "", shift_start: "09:00", shift_end: "17:00", maintenance_break_minutes: 0, day_of_week: null, is_active: true });
      fetchData(false);
    } catch (err) { alert("Failed: " + (err as Error).message); }
  };

  const handleDeleteShift = async (shiftId: number) => {
    if (!confirm("Delete this shift?")) return;
    try { await deleteShift(deviceId, shiftId); fetchData(false); } catch (err) { alert("Failed: " + (err as Error).message); }
  };

  if (loading) return <div className="p-8"><div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div></div></div>;
  if (error || !machine) return <div className="p-8"><div className="bg-red-50 border p-6 rounded"><h2 className="text-red-800 font-semibold">Error</h2><p className="text-red-600">{error || "Not found"}</p><Link href="/machines"><Button className="mt-4">Back</Button></Link></div></div>;

  const latestTelemetry = telemetry.at(-1);
  const dynamicMetrics = getDynamicMetrics(telemetry);

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
            <Link href="/machines" className="hover:text-slate-900">Machines</Link><span>/</span><span className="text-slate-900">{machine.name}</span>
          </div>
          <div className="flex items-start justify-between">
            <div><h1 className="text-2xl font-bold text-slate-900">{machine.name}</h1><p className="text-slate-500 font-mono mt-1">{machine.id}</p></div>
            <StatusBadge status={machine.status} />
          </div>
        </div>

        <div className="border-b border-slate-200 mb-6">
          <nav className="flex gap-8">
            {[{ id: "overview", label: "Overview" }, { id: "telemetry", label: "Telemetry" }, { id: "parameters", label: "Parameter Configuration" }, { id: "rules", label: "Configure Rules" }].map((tab) => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                className={`pb-4 text-sm font-medium border-b-2 ${activeTab === tab.id ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Machine Information</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                  <div><p className="text-sm text-slate-500">Name</p><p className="text-sm font-medium mt-1">{machine.name}</p></div>
                  <div><p className="text-sm text-slate-500">ID</p><p className="text-sm font-mono mt-1">{machine.id}</p></div>
                  <div><p className="text-sm text-slate-500">Type</p><p className="text-sm font-medium mt-1 capitalize">{machine.type}</p></div>
                  <div><p className="text-sm text-slate-500">Location</p><p className="text-sm font-medium mt-1">{machine.location || "—"}</p></div>
                  <div><p className="text-sm text-slate-500">Uptime</p><div className="mt-1"><UptimeCircle uptime={uptime} onClick={() => setActiveTab("parameters")} /></div></div>
                </div>
              </CardContent>
            </Card>

            {dynamicMetrics.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {dynamicMetrics.map((metric) => {
                  const value = (latestTelemetry as any)[metric];
                  if (typeof value !== 'number') return null;
                  const range = METRIC_RANGES[metric] || [0, 100];
                  return <RealTimeGauge key={metric} value={value} label={METRIC_LABELS[metric] || metric} unit={METRIC_UNITS[metric] || ""} min={range[0]} max={range[1]} color={METRIC_COLORS[metric] || "#2563eb"} />;
                })}
              </div>
            )}

            {telemetry.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {dynamicMetrics.map((metric) => {
                  const data = getMetricData(telemetry, metric);
                  if (data.length === 0) return null;
                  return <Card key={metric}><CardHeader><CardTitle>{METRIC_LABELS[metric] || metric} Trend</CardTitle></CardHeader><CardContent><TimeSeriesChart data={data} color={METRIC_COLORS[metric] || "#2563eb"} unit={METRIC_UNITS[metric] || ""} /></CardContent></Card>;
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === "telemetry" && (
          <div className="space-y-6">
            {telemetry.length === 0 ? <Card><CardContent className="py-12 text-center text-slate-500">No data</CardContent></Card> : (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Recent Telemetry</CardTitle>
                  <span className="text-xs text-slate-400">Auto-refresh every 1s • {telemetry.length} records</span>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200">
                      <thead className="bg-slate-50"><tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Timestamp</th>
                        {dynamicMetrics.map((m) => <th key={m} className="px-6 py-3 text-left text-xs font-medium text-slate-500">{METRIC_LABELS[m] || m}</th>)}
                      </tr></thead>
                      <tbody className="bg-white divide-y">
                        {telemetry.slice().reverse().slice(0, 20).map((point, i) => (
                          <tr key={i} className={i === 0 ? "bg-blue-50" : ""}>
                            <td className="px-6 py-3 text-sm font-mono">{formatTimestamp(point.timestamp)}</td>
                            {dynamicMetrics.map((m) => <td key={m} className="px-6 py-3 text-sm">{(point as any)[m]?.toFixed(2) ?? "—"}</td>)}
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

        {activeTab === "parameters" && (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Shift Configuration</CardTitle>
                <Button onClick={() => setShowAddShift(!showAddShift)}>{showAddShift ? "Cancel" : "+ Add Shift"}</Button>
              </CardHeader>
              <CardContent>
                {showAddShift && (
                  <div className="bg-slate-50 p-4 rounded-lg mb-6 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div><label className="block text-sm font-medium mb-1">Shift Name</label><input type="text" value={newShift.shift_name} onChange={(e) => setNewShift({ ...newShift, shift_name: e.target.value })} placeholder="e.g., Morning Shift" className="w-full px-3 py-2 border rounded-md" /></div>
                      <div><label className="block text-sm font-medium mb-1">Day of Week</label><select value={newShift.day_of_week ?? ""} onChange={(e) => setNewShift({ ...newShift, day_of_week: e.target.value ? parseInt(e.target.value) : null })} className="w-full px-3 py-2 border rounded-md">{DAYS_OF_WEEK.map(d => <option key={d.value ?? "all"} value={d.value ?? ""}>{d.label}</option>)}</select></div>
                      <div><label className="block text-sm font-medium mb-1">Start Time</label><input type="time" value={newShift.shift_start} onChange={(e) => setNewShift({ ...newShift, shift_start: e.target.value })} className="w-full px-3 py-2 border rounded-md" /></div>
                      <div><label className="block text-sm font-medium mb-1">End Time</label><input type="time" value={newShift.shift_end} onChange={(e) => setNewShift({ ...newShift, shift_end: e.target.value })} className="w-full px-3 py-2 border rounded-md" /></div>
                      <div><label className="block text-sm font-medium mb-1">Maintenance Break (min)</label><input type="number" min="0" max="480" value={newShift.maintenance_break_minutes} onChange={(e) => setNewShift({ ...newShift, maintenance_break_minutes: parseInt(e.target.value) || 0 })} className="w-full px-3 py-2 border rounded-md" /></div>
                    </div>
                    <Button onClick={handleAddShift} disabled={!newShift.shift_name}>Save Shift</Button>
                  </div>
                )}
                {shifts.length === 0 ? <div className="text-center py-8 text-slate-500">No shifts configured</div> : (
                  <div className="space-y-4">
                    {shifts.map((shift) => (
                      <div key={shift.id} className={`flex items-center justify-between p-4 rounded-lg border ${shift.is_active ? "bg-white" : "bg-slate-50 opacity-60"}`}>
                        <div>
                          <div className="flex items-center gap-2"><h3 className="font-medium">{shift.shift_name}</h3>{!shift.is_active && <span className="text-xs bg-slate-200 px-2 py-0.5 rounded">Inactive</span>}</div>
                          <p className="text-sm text-slate-500 mt-1">{shift.shift_start.slice(0,5)} - {shift.shift_end.slice(0,5)}{shift.maintenance_break_minutes > 0 && <span className="ml-2">(Break: {shift.maintenance_break_minutes} min)</span>}</p>
                          <p className="text-xs text-slate-400 mt-1">{DAYS_OF_WEEK.find(d => d.value === shift.day_of_week)?.label || "All Days"}</p>
                        </div>
                        <Button variant="danger" size="sm" onClick={() => handleDeleteShift(shift.id)}>Delete</Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "rules" && <MachineRulesView deviceId={deviceId} />}
      </div>
    </div>
  );
}
