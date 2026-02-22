"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { getDeviceById, Device, getShifts, createShift, deleteShift, Shift, ShiftCreate, getUptime, UptimeData, getHealthConfigs, createHealthConfig, deleteHealthConfig, updateHealthConfig, HealthConfig, HealthConfigCreate, calculateHealthScore, HealthScore, TelemetryValues, validateHealthWeights, WeightValidation } from "@/lib/deviceApi";
import { getTelemetry, TelemetryPoint } from "@/lib/dataApi";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RealTimeGauge } from "@/components/charts/Gauge";
import { TimeSeriesChart } from "@/components/charts/telemetry-charts";
import { MachineRulesView } from "@/app/machines/[deviceId]/rules/machine-rules-view";
import { formatIST, getRelativeTime } from "@/lib/utils";

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

function HealthScoreCircle({ healthScore, onClick }: { healthScore: HealthScore | null; onClick: () => void }) {
  const score = healthScore?.health_score ?? 0;
  const statusColor = healthScore?.status_color || "⚪";
  
  const colorMap: Record<string, string> = {
    "🟢": "#22c55e", "🟡": "#eab308", "🟠": "#f97316", "🔴": "#ef4444", "⚪": "#94a3b8"
  };
  const color = healthScore ? colorMap[statusColor] || "#94a3b8" : "#94a3b8";
  const isStandby = healthScore?.status === "Standby";
  
  return (
    <div className="relative cursor-pointer group" onClick={onClick}>
      <div className="w-16 h-16">
        <svg className="w-full h-full transform -rotate-90">
          <circle cx="32" cy="32" r="28" stroke="#e2e8f0" strokeWidth="6" fill="none" />
          <circle cx="32" cy="32" r="28" stroke={color} strokeWidth="6" fill="none"
            strokeDasharray={`${(score / 100) * 176} 176`} className="transition-all duration-500" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-bold">{isStandby ? "—" : `${score.toFixed(0)}%`}</span>
          <span className="text-[10px]">{isStandby ? "Standby" : statusColor}</span>
        </div>
      </div>
      
      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 w-56 bg-white shadow-lg rounded-lg border p-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
        <p className="text-xs font-semibold text-slate-700 mb-2">Health Score Details</p>
        {healthScore ? (
          <>
            <p className="text-xs text-slate-600">Status: <span className="font-medium">{healthScore.status} {healthScore.status_color}</span></p>
            <p className="text-xs text-slate-600">Machine State: <span className="font-medium">{healthScore.machine_state}</span></p>
            <p className="text-xs text-slate-600">Parameters: <span className="font-medium">{healthScore.parameters_included} included, {healthScore.parameters_skipped} skipped</span></p>
            <p className="text-xs text-slate-600">Total Weight: <span className="font-medium">{healthScore.total_weight_configured}%</span></p>
            {healthScore.parameter_scores.length > 0 && (
              <div className="mt-2 border-t pt-2">
                <p className="text-xs font-medium text-slate-700">Parameter Scores:</p>
                {healthScore.parameter_scores.slice(0, 5).map((p) => (
                  <p key={p.parameter_name} className="text-xs text-slate-600">
                    {p.parameter_name}: {p.raw_score}% {p.status_color}
                  </p>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="text-xs text-slate-500">No health data</p>
        )}
      </div>
    </div>
  );
}

function ParameterEfficiencyCard({ 
  metric, 
  value, 
  healthConfig,
  onConfigure 
}: { 
  metric: string; 
  value: number; 
  healthConfig: HealthConfig | null;
  onConfigure: () => void;
}) {
  const range = METRIC_RANGES[metric] || [0, 100];
  
  const getEfficiencyStatus = (rawScore: number): { label: string; color: string; bgColor: string } => {
    if (rawScore >= 85) return { label: "Healthy", color: "text-green-600", bgColor: "bg-green-50" };
    if (rawScore >= 70) return { label: "Slight Warning", color: "text-yellow-600", bgColor: "bg-yellow-50" };
    if (rawScore >= 40) return { label: "Warning", color: "text-orange-600", bgColor: "bg-orange-50" };
    return { label: "Critical", color: "text-red-600", bgColor: "bg-red-50" };
  };
  
  const calculateScore = (val: number, config: HealthConfig): number => {
    const { normal_min, normal_max, max_min, max_max } = config;
    if (normal_min === null || normal_max === null) return 100;
    
    const idealCenter = (normal_min + normal_max) / 2;
    const halfRange = (normal_max - normal_min) / 2 || 1;
    
    if (val >= normal_min && val <= normal_max) {
      const deviation = Math.abs(val - idealCenter);
      const score = 100 - (deviation / halfRange) * 30;
      return Math.max(70, Math.min(100, score));
    }
    
    if (max_min !== null && max_max !== null) {
      if (val < normal_min) {
        if (val < max_min) return Math.max(0, 25 - (max_min - val) * 10);
        const overshoot = normal_min - val;
        const tolerance = normal_min - max_min || 1;
        return Math.max(25, Math.min(69, 70 - (overshoot / tolerance) * 45));
      } else {
        if (val > max_max) return Math.max(0, 25 - (val - max_max) * 10);
        const overshoot = val - normal_max;
        const tolerance = max_max - normal_max || 1;
        return Math.max(25, Math.min(69, 70 - (overshoot / tolerance) * 45));
      }
    }
    
    const deviation = val < normal_min ? normal_min - val : val - normal_max;
    return Math.max(25, Math.min(69, 70 - deviation * 10));
  };
  
  const hasConfig = healthConfig !== null;
  const score = hasConfig ? calculateScore(value, healthConfig) : null;
  const status = score !== null ? getEfficiencyStatus(score) : null;
  
  return (
    <div className="p-4 rounded-lg border bg-white">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-sm">{METRIC_LABELS[metric] || metric}</h4>
        {!hasConfig && (
          <button onClick={onConfigure} className="text-xs text-blue-600 hover:underline">
            Configure
          </button>
        )}
      </div>
      <div className="text-2xl font-bold mb-2">
        {value.toFixed(2)}{METRIC_UNITS[metric] || ""}
      </div>
      {hasConfig && score !== null && status && (
        <div className={`text-sm ${status.color} ${status.bgColor} px-2 py-1 rounded inline-flex items-center gap-1`}>
          Efficiency: {score.toFixed(0)}% {status.color.includes("green") ? "🟢" : status.color.includes("yellow") ? "🟡" : status.color.includes("orange") ? "🟠" : "🔴"}
        </div>
      )}
      {hasConfig && (
        <div className="mt-2 text-xs text-slate-500">
          Normal: {healthConfig.normal_min} - {healthConfig.normal_max} | Weight: {healthConfig.weight}%
        </div>
      )}
    </div>
  );
}

function HealthConfigModal({ 
  isOpen, 
  onClose, 
  deviceId, 
  metric,
  existingConfig,
  allConfigs,
  onSave,
  onDelete 
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  deviceId: string;
  metric: string;
  existingConfig: HealthConfig | null;
  allConfigs: HealthConfig[];
  onSave: (config: HealthConfigCreate) => void;
  onDelete: (configId: number) => void;
}) {
  const [formData, setFormData] = useState<HealthConfigCreate>({
    parameter_name: "",
    normal_min: undefined,
    normal_max: undefined,
    max_min: undefined,
    max_max: undefined,
    weight: 0,
    ignore_zero_value: false,
    is_active: true,
  });
  
  useEffect(() => {
    if (!metric) return;
    
    if (existingConfig) {
      setFormData({
        parameter_name: existingConfig.parameter_name,
        normal_min: existingConfig.normal_min ?? undefined,
        normal_max: existingConfig.normal_max ?? undefined,
        max_min: existingConfig.max_min ?? undefined,
        max_max: existingConfig.max_max ?? undefined,
        weight: existingConfig.weight,
        ignore_zero_value: existingConfig.ignore_zero_value,
        is_active: existingConfig.is_active,
      });
    } else {
      const defaultRanges: Record<string, { normal: [number, number]; max: [number, number] }> = {
        pressure: { normal: [2, 6], max: [0, 10] },
        temperature: { normal: [20, 60], max: [0, 100] },
        vibration: { normal: [0, 3], max: [0, 8] },
        power: { normal: [100, 400], max: [0, 500] },
        voltage: { normal: [210, 240], max: [180, 260] },
        current: { normal: [2, 15], max: [0, 20] },
        frequency: { normal: [48, 52], max: [40, 60] },
        power_factor: { normal: [0.85, 1.0], max: [0.5, 1.0] },
        speed: { normal: [1200, 1800], max: [800, 2200] },
        torque: { normal: [50, 300], max: [0, 500] },
        oil_pressure: { normal: [1, 4], max: [0, 5] },
        humidity: { normal: [30, 70], max: [0, 100] },
      };
      
      const defaults = defaultRanges[metric];
      
      setFormData({
        parameter_name: metric,
        normal_min: defaults?.normal[0] ?? undefined,
        normal_max: defaults?.normal[1] ?? undefined,
        max_min: defaults?.max[0] ?? undefined,
        max_max: defaults?.max[1] ?? undefined,
        weight: 0,
        ignore_zero_value: false,
        is_active: true,
      });
    }
  }, [metric, existingConfig]);
  
  if (!isOpen) return null;
  
  const totalWeight = allConfigs
    .filter(c => c.is_active && c.parameter_name !== metric)
    .reduce((sum, c) => sum + c.weight, 0) + formData.weight;
  
  const otherWeightsSum = allConfigs
    .filter(c => c.is_active && c.parameter_name !== metric)
    .reduce((sum, c) => sum + c.weight, 0);
  
  const remainingWeight = 100 - otherWeightsSum;
  const currentWeight = existingConfig?.weight || 0;
  const maxAllowedWeight = remainingWeight + currentWeight;
  const isWeightValid = Math.abs(totalWeight - 100) < 0.01;
  
  const handleWeightChange = (value: number) => {
    // Allow any value that's within the allowed range (remaining + current weight)
    // This allows decreasing weight when editing
    if (!isNaN(value) && value >= 0 && value <= maxAllowedWeight) {
      setFormData({ ...formData, weight: value });
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Configure Health: {metric}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>
        
        <div className="space-y-4">
          <div className="p-3 bg-blue-50 rounded text-sm">
            <p className="font-medium text-blue-800 mb-2">Normal Range (Optimal)</p>
            <p className="text-blue-600 text-xs">Values here get 70-100% efficiency score</p>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Normal Min</label>
              <input type="number" step="0.1" value={formData.normal_min ?? ""} onChange={(e) => setFormData({ ...formData, normal_min: e.target.value ? parseFloat(e.target.value) : undefined })} className="w-full px-3 py-2 border rounded-md" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Normal Max</label>
              <input type="number" step="0.1" value={formData.normal_max ?? ""} onChange={(e) => setFormData({ ...formData, normal_max: e.target.value ? parseFloat(e.target.value) : undefined })} className="w-full px-3 py-2 border rounded-md" />
            </div>
          </div>
          
          <div className="p-3 bg-orange-50 rounded text-sm">
            <p className="font-medium text-orange-800 mb-2">Maximum Range (Limits)</p>
            <p className="text-orange-600 text-xs">Values outside normal but within max get 25-69% score</p>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Max Min</label>
              <input type="number" step="0.1" value={formData.max_min ?? ""} onChange={(e) => setFormData({ ...formData, max_min: e.target.value ? parseFloat(e.target.value) : undefined })} className="w-full px-3 py-2 border rounded-md" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Max</label>
              <input type="number" step="0.1" value={formData.max_max ?? ""} onChange={(e) => setFormData({ ...formData, max_max: e.target.value ? parseFloat(e.target.value) : undefined })} className="w-full px-3 py-2 border rounded-md" />
            </div>
          </div>
          
            <div className="border-t pt-4">
              <label className="block text-sm font-medium mb-1">
                Weight (%) 
                {existingConfig && <span className="text-xs text-slate-500 font-normal ml-2">(Saved: {currentWeight}%, Max: {maxAllowedWeight}%)</span>}
              </label>
              <input 
                type="number" 
                min="0" 
                max={maxAllowedWeight}
                step="1" 
                value={formData.weight} 
                onChange={(e) => handleWeightChange(parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 border rounded-md" 
              />
              <div className={`text-xs mt-2 p-2 rounded ${isWeightValid ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                <p>Total Weight: <strong>{totalWeight.toFixed(1)}%</strong> / 100%</p>
                <p>Remaining: <strong>{remainingWeight.toFixed(1)}%</strong></p>
                {!isWeightValid && <p className="mt-1">⚠️ Total must equal 100% to calculate health score</p>}
                {isWeightValid && <p className="mt-1">✓ Weight configured correctly</p>}
              </div>
            </div>
          
          <div className="flex items-center gap-2">
            <input type="checkbox" id="ignoreZero" checked={formData.ignore_zero_value} onChange={(e) => setFormData({ ...formData, ignore_zero_value: e.target.checked })} className="rounded" />
            <label htmlFor="ignoreZero" className="text-sm">Ignore zero values (exclude from scoring when machine is off)</label>
          </div>
          
          {existingConfig && (
            <Button variant="danger" className="w-full" onClick={() => onDelete(existingConfig.id)}>
              Delete Configuration
            </Button>
          )}
        </div>
        
        <div className="flex gap-2 mt-6">
          <Button variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
          <Button onClick={() => onSave(formData)} className="flex-1">
            {isWeightValid ? "Save" : `Save (${totalWeight.toFixed(0)}%)`}
          </Button>
        </div>
        {!isWeightValid && (
          <p className="text-xs text-center mt-2 text-amber-600">
            ⚠️ Note: Health score will only calculate when total weight = 100%
          </p>
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
  const [healthConfigs, setHealthConfigs] = useState<HealthConfig[]>([]);
  const [healthScore, setHealthScore] = useState<HealthScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "telemetry" | "parameters" | "rules">("overview");
  const [showAddShift, setShowAddShift] = useState(false);
  const [showHealthConfig, setShowHealthConfig] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState<string>("");
  const [newShift, setNewShift] = useState<ShiftCreate>({
    shift_name: "", shift_start: "09:00", shift_end: "17:00", maintenance_break_minutes: 0, day_of_week: null, is_active: true,
  });
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);

  const fetchData = async (isInitial = false) => {
    try {
      const [machineData, telemetryData, uptimeData, shiftsData, healthConfigsData] = await Promise.all([
        getDeviceById(deviceId),
        getTelemetry(deviceId, { limit: "100" }),
        getUptime(deviceId),
        getShifts(deviceId),
        getHealthConfigs(deviceId),
      ]);
      // Always update machine data to get latest last_seen_timestamp
      setMachine(machineData);
      setTelemetry(telemetryData);
      setUptime(uptimeData);
      setShifts(shiftsData);
      setHealthConfigs(healthConfigsData);
      
      const latest = telemetryData.at(-1);
      if (latest && healthConfigsData.length > 0) {
        const telemetryValues: TelemetryValues = {
          values: {},
          machine_state: "RUNNING",
        };
        
        for (const [key, val] of Object.entries(latest)) {
          if (typeof val === 'number') {
            telemetryValues.values[key] = val;
          }
        }
        
        try {
          const score = await calculateHealthScore(deviceId, telemetryValues);
          setHealthScore(score);
        } catch (e) {
          console.error("Health score error:", e);
        }
      }
      
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

  const handleSaveHealthConfig = async (config: HealthConfigCreate) => {
    try {
      const existing = healthConfigs.find(c => c.parameter_name === config.parameter_name);
      if (existing) {
        await updateHealthConfig(deviceId, existing.id, config);
      } else {
        await createHealthConfig(deviceId, config);
      }
      setShowHealthConfig(false);
      setSelectedMetric("");
      fetchData(false);
    } catch (err) { alert("Failed: " + (err as Error).message); }
  };

  const handleDeleteHealthConfig = async (configId: number) => {
    try {
      await deleteHealthConfig(deviceId, configId);
      setShowHealthConfig(false);
      setSelectedMetric("");
      fetchData(false);
    } catch (err) { alert("Failed: " + (err as Error).message); }
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
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{machine.name}</h1>
              <p className="text-slate-500 font-mono mt-1">{machine.id}</p>
              {machine.last_seen_timestamp ? (
                <p className="text-xs text-slate-500 mt-1">
                  Last seen: {formatIST(machine.last_seen_timestamp)}
                </p>
              ) : (
                <p className="text-xs text-slate-500 mt-1">Last seen: No data received</p>
              )}
            </div>
            <StatusBadge status={machine.runtime_status} />
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
                <div className="grid grid-cols-2 md:grid-cols-6 gap-6">
                  <div><p className="text-sm text-slate-500">Name</p><p className="text-sm font-medium mt-1">{machine.name}</p></div>
                  <div><p className="text-sm text-slate-500">ID</p><p className="text-sm font-mono mt-1">{machine.id}</p></div>
                  <div><p className="text-sm text-slate-500">Type</p><p className="text-sm font-medium mt-1 capitalize">{machine.type}</p></div>
                  <div><p className="text-sm text-slate-500">Location</p><p className="text-sm font-medium mt-1">{machine.location || "—"}</p></div>
                  <div><p className="text-sm text-slate-500">Uptime</p><div className="mt-1"><UptimeCircle uptime={uptime} onClick={() => setActiveTab("parameters")} /></div></div>
                  <div><p className="text-sm text-slate-500">Health</p><div className="mt-1"><HealthScoreCircle healthScore={healthScore} onClick={() => setActiveTab("parameters")} /></div></div>
                </div>
              </CardContent>
            </Card>

            {dynamicMetrics.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {dynamicMetrics.map((metric) => {
                  const value = (latestTelemetry as any)[metric];
                  if (typeof value !== 'number') return null;
                  const range = METRIC_RANGES[metric] || [0, 100];
                  return (
                    <div key={metric} className="space-y-2">
                      <RealTimeGauge value={value} label={METRIC_LABELS[metric] || metric} unit={METRIC_UNITS[metric] || ""} min={range[0]} max={range[1]} color={METRIC_COLORS[metric] || "#2563eb"} />
                      <ParameterEfficiencyCard 
                        metric={metric} 
                        value={value} 
                        healthConfig={healthConfigs.find(c => c.parameter_name === metric) || null}
                        onConfigure={() => { setSelectedMetric(metric); setShowHealthConfig(true); }}
                      />
                    </div>
                  );
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

            <Card>
              <CardHeader>
                <CardTitle>Parameter Health Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-800"><strong>Health Score:</strong> Configurable ranges and weights for each parameter. The overall health score (0-100%) is calculated when the machine is RUNNING.</p>
                  <p className="text-sm text-blue-800 mt-1"><strong>Machine State:</strong> Health scoring only activates when machine_state = RUNNING. For OFF, IDLE, UNLOAD, POWER CUT states, the score shows as "Standby".</p>
                  <p className="text-sm text-blue-800 mt-1"><strong>Weights:</strong> All active parameter weights must sum to 100%.</p>
                </div>
                
                {dynamicMetrics.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {dynamicMetrics.map((metric) => {
                      const config = healthConfigs.find(c => c.parameter_name === metric);
                      return (
                        <div key={metric} className={`p-4 rounded-lg border ${config?.is_active ? "bg-white" : "bg-slate-50 opacity-60"}`}>
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium">{METRIC_LABELS[metric] || metric}</h4>
                            {config && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Configured</span>}
                          </div>
                          {config ? (
                            <div className="text-sm text-slate-600 space-y-1">
                              <p>Normal: {config.normal_min ?? "—"} - {config.normal_max ?? "—"}</p>
                              <p>Max: {config.max_min ?? "—"} - {config.max_max ?? "—"}</p>
                              <p>Weight: {config.weight}%</p>
                              <p>Ignore Zero: {config.ignore_zero_value ? "Yes" : "No"}</p>
                            </div>
                          ) : (
                            <p className="text-sm text-slate-500">Not configured</p>
                          )}
                          <Button size="sm" className="mt-3 w-full" onClick={() => { setSelectedMetric(metric); setShowHealthConfig(true); }}>
                            {config ? "Edit" : "Configure"}
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">No telemetry parameters available</div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "rules" && <MachineRulesView deviceId={deviceId} />}
      </div>
      
      <HealthConfigModal
        isOpen={showHealthConfig}
        onClose={() => { setShowHealthConfig(false); setSelectedMetric(""); }}
        deviceId={deviceId}
        metric={selectedMetric}
        existingConfig={healthConfigs.find(c => c.parameter_name === selectedMetric) || null}
        allConfigs={healthConfigs}
        onSave={handleSaveHealthConfig}
        onDelete={handleDeleteHealthConfig}
      />
    </div>
  );
}
