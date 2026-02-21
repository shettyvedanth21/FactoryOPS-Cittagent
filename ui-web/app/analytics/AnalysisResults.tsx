"use client";

import { Badge } from "@/components/ui/badge";
import {
  AnomalyChart,
} from "@/components/charts/telemetry-charts";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type Props = {
  results: any;
  analysisType: "anomaly" | "prediction" | "forecast";
};

export function AnalysisResults({ results, analysisType }: Props) {

  /* ---------------- anomaly ---------------- */

  if (analysisType === "anomaly") {

    const points = results?.results?.points ?? [];

    if (!points.length) {
      return <p className="text-sm text-slate-500">No result points available</p>;
    }

    const total = points.length;
    const anomalies = points.filter((p: any) => p.is_anomaly).length;
    const percent = (anomalies / total) * 100;

    const chartData = points.map((p: any) => ({
      timestamp: p.timestamp,
      value: p.value ?? 0,
      isAnomaly: p.is_anomaly,
      anomalyScore: p.anomaly_score,
    }));

    return (
      <div className="space-y-6">

        {/* KPI */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-sm text-slate-500">Total points</p>
            <p className="text-2xl font-bold">{total}</p>
          </div>

          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-sm text-slate-500">Total anomalies</p>
            <p className="text-2xl font-bold">{anomalies}</p>
          </div>

          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-sm text-slate-500">Anomaly percentage</p>
            <p className="text-2xl font-bold">
              {percent.toFixed(2)}%
            </p>
          </div>

        </div>

        <AnomalyChart
          title="Anomaly Detection"
          data={chartData}
        />

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs">Timestamp</th>
                <th className="px-4 py-2 text-left text-xs">Status</th>
                <th className="px-4 py-2 text-left text-xs">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {points.map((p: any, i: number) => (
                <tr key={i}>
                  <td className="px-4 py-2 text-sm font-mono">
                    {new Date(p.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    <Badge variant={p.is_anomaly ? "error" : "success"}>
                      {p.is_anomaly ? "Anomaly" : "Normal"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {typeof p.anomaly_score === "number"
                      ? p.anomaly_score.toFixed(4)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    );
  }

  /* ---------------- prediction ---------------- */

  if (analysisType === "prediction") {

    const points = results?.results?.points ?? [];

    if (!points.length) {
      return <p className="text-sm text-slate-500">No result points available</p>;
    }

    const chartData = points.map((p: any) => ({
      timestamp: p.timestamp,
      probability: p.failure_probability * 100,
    }));

    return (
      <div className="space-y-6">

        <div className="w-full">
          <h4 className="text-sm font-medium text-slate-700 mb-4">
            Failure probability trend
          </h4>

          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(t) =>
                  new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                }
              />
              <YAxis unit="%" />
              <Tooltip
                labelFormatter={(l) => new Date(l).toLocaleString()}
                formatter={(v: any) => [`${v.toFixed(2)}%`, "Probability"]}
              />
              <Line
                type="monotone"
                dataKey="probability"
                stroke="#2563eb"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs">Timestamp</th>
                <th className="px-4 py-2 text-left text-xs">Failure</th>
                <th className="px-4 py-2 text-left text-xs">Probability</th>
                <th className="px-4 py-2 text-left text-xs">TTF (hours)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {points.map((p: any, i: number) => (
                <tr key={i}>
                  <td className="px-4 py-2 text-sm font-mono">
                    {new Date(p.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    <Badge variant={p.predicted_failure ? "error" : "success"}>
                      {p.predicted_failure ? "Yes" : "No"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {(p.failure_probability * 100).toFixed(2)}%
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {p.time_to_failure_hours}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    );
  }

  /* ---------------- forecast ---------------- */

  const values: number[] = results?.results?.forecast ?? [];

  if (!values.length) {
    return <p className="text-sm text-slate-500">No forecast values available</p>;
  }

  const forecastSeries = values.map((v, i) => ({
    step: i + 1,
    value: v,
  }));

  return (
    <div className="space-y-6">

      <div className="w-full">
        <h4 className="text-sm font-medium text-slate-700 mb-4">
          Forecast horizon
        </h4>

        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={forecastSeries}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="step"
              tickFormatter={(v) => `t+${v}`}
            />
            <YAxis />
            <Tooltip
              formatter={(v: any) => [v.toFixed(3), "Forecast"]}
              labelFormatter={(l) => `t+${l}`}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs">Step</th>
              <th className="px-4 py-2 text-left text-xs">Forecast</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {forecastSeries.map((p) => (
              <tr key={p.step}>
                <td className="px-4 py-2 text-sm font-mono">
                  t+{p.step}
                </td>
                <td className="px-4 py-2 text-sm">
                  {p.value.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}