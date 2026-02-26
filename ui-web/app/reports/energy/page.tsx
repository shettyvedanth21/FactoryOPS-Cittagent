"use client";

import { useState, useCallback } from "react";
import { DateRangeSelector } from "@/components/reports/DateRangeSelector";
import { DeviceMultiSelect } from "@/components/reports/DeviceMultiSelect";
import { ReportProgress } from "@/components/reports/ReportProgress";
import { ErrorPanel } from "@/components/reports/ErrorPanel";
import {
  submitConsumptionReport,
  getReportDownload,
} from "@/lib/reportApi";

const DEFAULT_TENANT_ID = "tenant1";

type ViewState = "empty" | "processing" | "completed" | "failed";

interface ReportResult {
  energy: {
    data: {
      total_kwh: number;
      avg_power_w: number;
      peak_power_w: number;
      min_power_w: number;
    };
    success: boolean;
  };
  demand: {
    data: {
      peak_demand_kw: number;
      peak_demand_timestamp: string;
    };
    success: boolean;
  };
  load_factor: {
    data: {
      load_factor: number;
      classification: string;
      recommendation: string;
    };
    success: boolean;
  };
  cost: {
    total_cost: number;
    currency: string;
  };
  insights: string[];
  daily_series: Array<{ date: string; kwh: number }>;
}

export default function EnergyReportPage() {
  const [viewState, setViewState] = useState<ViewState>("empty");
  const [reportId, setReportId] = useState<string | null>(null);
  const [result, setResult] = useState<ReportResult | null>(null);
  const [error, setError] = useState<{ error_code: string; error_message: string } | null>(null);

  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [deviceIds, setDeviceIds] = useState<string[]>([]);
  const [groupBy, setGroupBy] = useState<"daily" | "weekly">("daily");
  const [submitting, setSubmitting] = useState(false);

  const handleRangeChange = useCallback((start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  }, []);

  const handleDeviceChange = useCallback((ids: string[]) => {
    setDeviceIds(ids);
  }, []);

  const handleSubmit = async () => {
    if (!startDate || !endDate || deviceIds.length === 0) return;

    setSubmitting(true);
    setError(null);

    try {
      const response = await submitConsumptionReport({
        tenant_id: DEFAULT_TENANT_ID,
        device_ids: deviceIds,
        start_date: startDate,
        end_date: endDate,
        group_by: groupBy,
      });

      setReportId(response.report_id);
      setViewState("processing");
    } catch (err) {
      setError({
        error_code: "SUBMIT_ERROR",
        error_message: err instanceof Error ? err.message : "Failed to submit report",
      });
      setViewState("failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleComplete = (reportResult: unknown) => {
    setResult(reportResult as ReportResult);
    setViewState("completed");
  };

  const handleError = (err: { error_code: string; error_message: string }) => {
    setError(err);
    setViewState("failed");
  };

  const handleRetry = () => {
    setViewState("empty");
    setReportId(null);
    setResult(null);
    setError(null);
  };

  const handleDownload = async () => {
    if (!reportId) {
      alert("No report ID");
      return;
    }
    try {
      console.log("Starting download for report:", reportId);
      const blob = await getReportDownload(reportId, DEFAULT_TENANT_ID);
      console.log("Got blob:", blob.type, blob.size);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `energy_report_${reportId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      console.log("Download triggered");
    } catch (err) {
      console.error("Failed to download report:", err);
      alert(`Failed to download report: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const isFormValid = startDate && endDate && deviceIds.length > 0 && !submitting;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Energy Consumption Report</h1>
        <p className="text-gray-600 mt-1">Generate detailed energy analysis report</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          {viewState === "empty" && (
            <>
              <div className="bg-white p-4 rounded-lg border">
                <h3 className="font-medium text-gray-900 mb-3">Date Range</h3>
                <DateRangeSelector
                  onRangeChange={handleRangeChange}
                  disabled={submitting}
                />
              </div>

              <div className="bg-white p-4 rounded-lg border">
                <h3 className="font-medium text-gray-900 mb-3">Devices</h3>
                <DeviceMultiSelect
                  tenantId={DEFAULT_TENANT_ID}
                  onChange={handleDeviceChange}
                  disabled={submitting}
                />
              </div>

              <div className="bg-white p-4 rounded-lg border">
                <h3 className="font-medium text-gray-900 mb-3">Group By</h3>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="groupBy"
                      value="daily"
                      checked={groupBy === "daily"}
                      onChange={() => setGroupBy("daily")}
                      disabled={submitting}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Daily</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="groupBy"
                      value="weekly"
                      checked={groupBy === "weekly"}
                      onChange={() => setGroupBy("weekly")}
                      disabled={submitting}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Weekly</span>
                  </label>
                </div>
              </div>

              <button
                onClick={handleSubmit}
                disabled={!isFormValid}
                className={`w-full py-3 rounded-lg font-medium transition-colors ${
                  isFormValid
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-200 text-gray-500 cursor-not-allowed"
                }`}
              >
                {submitting ? "Submitting..." : "Generate Report"}
              </button>
            </>
          )}

          {viewState === "processing" && reportId && (
            <ReportProgress
              reportId={reportId}
              tenantId={DEFAULT_TENANT_ID}
              onComplete={handleComplete}
              onError={handleError}
            />
          )}

          {viewState === "failed" && error && (
            <ErrorPanel
              errorCode={error.error_code}
              errorMessage={error.error_message}
              onRetry={handleRetry}
            />
          )}
        </div>

        <div className="bg-white rounded-lg border min-h-[400px] p-6">
          {viewState === "empty" && (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>Configure your report and click Generate</p>
            </div>
          )}

          {viewState === "completed" && result && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {result.energy?.data?.total_kwh?.toFixed(1) ?? "—"}
                  </div>
                  <div className="text-sm text-gray-600">Total kWh</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {result.demand?.data?.peak_demand_kw?.toFixed(1) ?? "—"}
                  </div>
                  <div className="text-sm text-gray-600">Peak kW</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {result.load_factor?.data?.load_factor 
                      ? (result.load_factor.data.load_factor * 100).toFixed(1) + "%" 
                      : "—"}
                  </div>
                  <div className="text-sm text-gray-600">Load Factor</div>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {result.cost?.currency} {result.cost?.total_cost?.toFixed(0) ?? "0"}
                  </div>
                  <div className="text-sm text-gray-600">Est. Cost</div>
                </div>
              </div>

              {result.insights && result.insights.length > 0 && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Key Insights</h3>
                  <ul className="space-y-2">
                    {result.insights.map((insight, idx) => (
                      <li key={idx} className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                        {insight}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                onClick={handleDownload}
                className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Download PDF
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
