"use client";

import { useState, useEffect } from "react";

interface DateRangeSelectorProps {
  onRangeChange: (start: string, end: string) => void;
  disabled?: boolean;
}

type TabMode = "presets" | "month" | "custom";

export function DateRangeSelector({ onRangeChange, disabled }: DateRangeSelectorProps) {
  const [mode, setMode] = useState<TabMode>("presets");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [selectedMonth, setSelectedMonth] = useState<string>("");

  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const formatDate = (d: Date): string => d.toISOString().split("T")[0];
  const formatDisplay = (d: Date): string =>
    d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });

  const presets = [
    { label: "Today", days: 0 },
    { label: "Yesterday", days: 1 },
    { label: "Last 7 days", days: 7 },
    { label: "Last 30 days", days: 30 },
    { label: "Last 90 days", days: 90 },
  ];

  const months: Date[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    months.push(d);
  }

  const handlePresetClick = (days: number) => {
    const end = new Date(today);
    const start = new Date(today);
    start.setDate(start.getDate() - days);
    setStartDate(formatDate(start));
    setEndDate(formatDate(end));
    onRangeChange(formatDate(start), formatDate(end));
  };

  const handleMonthClick = (monthDate: Date) => {
    const start = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
    const end = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
    setStartDate(formatDate(start));
    setEndDate(formatDate(end));
    setSelectedMonth(formatDate(monthDate));
    onRangeChange(formatDate(start), formatDate(end));
  };

  const handleCustomStartChange = (value: string) => {
    setStartDate(value);
    const start = new Date(value);
    const end = new Date(value);
    end.setDate(end.getDate() + 90);
    if (end > yesterday) end.setDate(yesterday.getDate());
    setEndDate(formatDate(end));
    onRangeChange(value, formatDate(end));
  };

  const handleCustomEndChange = (value: string) => {
    setEndDate(value);
    onRangeChange(startDate, value);
  };

  const minDate = formatDate(new Date(today.getTime() - 365 * 24 * 60 * 60 * 1000));
  const maxDate = formatDate(yesterday);
  const minEndDate = startDate ? formatDate(new Date(new Date(startDate).getTime() + 24 * 60 * 60 * 1000)) : "";
  const maxEndDate = startDate
    ? formatDate(
        new Date(
          Math.min(
            new Date(startDate).getTime() + 90 * 24 * 60 * 60 * 1000,
            yesterday.getTime()
          )
        )
      )
    : maxDate;

  const getDaysBetween = (): number => {
    if (!startDate || !endDate) return 0;
    const diff = new Date(endDate).getTime() - new Date(startDate).getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24)) + 1;
  };

  const getRangeSummary = (): string => {
    if (!startDate || !endDate) return "";
    const start = new Date(startDate);
    const end = new Date(endDate);
    const days = getDaysBetween();
    return `${formatDisplay(start)} – ${formatDisplay(end)} (${days} days)`;
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2 border-b">
        {(["presets", "month", "custom"] as TabMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            disabled={disabled}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mode === m
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {m === "presets" ? "Quick Presets" : m === "month" ? "Month Picker" : "Custom"}
          </button>
        ))}
      </div>

      <div className="p-4 bg-gray-50 rounded-lg">
        {mode === "presets" && (
          <div className="flex flex-wrap gap-2">
            {presets.map((p) => (
              <button
                key={p.label}
                onClick={() => handlePresetClick(p.days)}
                disabled={disabled}
                className="px-3 py-1.5 text-sm bg-white border rounded-md hover:bg-blue-50 hover:border-blue-300 transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        {mode === "month" && (
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
            {months.map((m) => (
              <button
                key={m.toISOString()}
                onClick={() => handleMonthClick(m)}
                disabled={disabled}
                className="px-3 py-2 text-sm bg-white border rounded-md hover:bg-blue-50 hover:border-blue-300 transition-colors"
              >
                {m.toLocaleDateString("en-GB", { month: "short", year: "2-digit" })}
              </button>
            ))}
          </div>
        )}

        {mode === "custom" && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => handleCustomStartChange(e.target.value)}
                min={minDate}
                max={maxDate}
                disabled={disabled}
                className="w-full px-3 py-2 border rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => handleCustomEndChange(e.target.value)}
                min={minEndDate}
                max={maxEndDate}
                disabled={disabled}
                className="w-full px-3 py-2 border rounded-md text-sm"
              />
            </div>
            {startDate && endDate && (
              <p className="text-sm text-gray-600">{getDaysBetween()} days selected</p>
            )}
          </div>
        )}
      </div>

      {startDate && endDate && (
        <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded-md">
          Selected: <strong>{getRangeSummary()}</strong>
        </div>
      )}
    </div>
  );
}
