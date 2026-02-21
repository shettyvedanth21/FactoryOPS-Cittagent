"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart,
  ReferenceLine,
} from "recharts";

interface TimeSeriesChartProps {
  data: Array<{ timestamp: string; value: number }>;
  dataKey?: string;
  title?: string;
  color?: string;
  unit?: string;
  showArea?: boolean;
  referenceLines?: Array<{ value: number; label: string; color: string }>;
}

export function TimeSeriesChart({
  data,
  dataKey = "value",
  title,
  color = "#2563eb",
  unit = "",
  showArea = false,
  referenceLines,
}: TimeSeriesChartProps) {
  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const ChartComponent = showArea ? AreaChart : LineChart;

  return (
    <div className="w-full">
      {title && <h4 className="text-sm font-medium text-slate-700 mb-4">{title}</h4>}
      <ResponsiveContainer width="100%" height={250}>
        <ChartComponent data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatDate}
            stroke="#64748b"
            fontSize={12}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickFormatter={(value) => `${value}${unit}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
            }}
            labelFormatter={(label) => new Date(label).toLocaleString()}
            formatter={(value) => [`${value}${unit}`, dataKey]}
          />
          <Legend />
          {showArea ? (
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              fill={color}
              fillOpacity={0.1}
              strokeWidth={2}
              dot={false}
            />
          ) : (
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          )}
          {referenceLines?.map((line, index) => (
            <ReferenceLine
              key={index}
              y={line.value}
              stroke={line.color}
              strokeDasharray="5 5"
              label={{ value: line.label, fill: line.color, fontSize: 12 }}
            />
          ))}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
}

interface MultiLineChartProps {
  data: Array<{ timestamp: string; [key: string]: number | string }>;
  lines: Array<{ key: string; name: string; color: string }>;
  title?: string;
}

export function MultiLineChart({ data, lines, title }: MultiLineChartProps) {
  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="w-full">
      {title && <h4 className="text-sm font-medium text-slate-700 mb-4">{title}</h4>}
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatDate}
            stroke="#64748b"
            fontSize={12}
          />
          <YAxis stroke="#64748b" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
            }}
            labelFormatter={(label) => new Date(label).toLocaleString()}
          />
          <Legend />
          {lines.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.name}
              stroke={line.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface AnomalyChartProps {
  data: Array<{
    timestamp: string;
    value: number;
    isAnomaly?: boolean;
    anomalyScore?: number;
  }>;
  title?: string;
}

export function AnomalyChart({ data, title }: AnomalyChartProps) {
  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="w-full">
      {title && <h4 className="text-sm font-medium text-slate-700 mb-4">{title}</h4>}
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatDate}
            stroke="#64748b"
            fontSize={12}
          />
          <YAxis stroke="#64748b" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
            }}
            labelFormatter={(label) => new Date(label).toLocaleString()}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            name="Value"
            stroke="#2563eb"
            strokeWidth={2}
            dot={(props) => {
              const { payload } = props;
              if (payload?.isAnomaly) {
                return (
                  <circle cx={props.cx} cy={props.cy} r={4} fill="#dc2626" />
                );
              }
              return <></>;
            }}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="anomalyScore"
            name="Anomaly Score"
            stroke="#dc2626"
            strokeDasharray="5 5"
            strokeWidth={1}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface ForecastChartProps {
  data: Array<{
    timestamp: string;
    actual?: number;
    forecast?: number;
    upperBound?: number;
    lowerBound?: number;
  }>;
  title?: string;
}

export function ForecastChart({ data, title }: ForecastChartProps) {
  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div className="w-full">
      {title && <h4 className="text-sm font-medium text-slate-700 mb-4">{title}</h4>}
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatDate}
            stroke="#64748b"
            fontSize={12}
          />
          <YAxis stroke="#64748b" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
            }}
            labelFormatter={(label) => new Date(label).toLocaleString()}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="actual"
            name="Actual"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            name="Forecast"
            stroke="#16a34a"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
          />
          <Area
            type="monotone"
            dataKey="upperBound"
            stroke="none"
            fill="#16a34a"
            fillOpacity={0.1}
          />
          <Area
            type="monotone"
            dataKey="lowerBound"
            stroke="none"
            fill="white"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
