"use client";

import { useState, useCallback, useEffect } from "react";
import { getDevices, Device } from "@/lib/deviceApi";
import { DateRangeSelector } from "@/components/reports/DateRangeSelector";
import { ReportProgress } from "@/components/reports/ReportProgress";
import { ErrorPanel } from "@/components/reports/ErrorPanel";
import {
  submitComparisonReport,
  getReportDownload,
  ComparisonReportParams,
} from "@/lib/reportApi";

const DEFAULT_TENANT_ID = "tenant1";

type ComparisonType = "machine_vs_machine" | "period_vs_period";
type ViewState = "form" | "processing" | "completed" | "failed";

export default function CompareReportPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);

  const [comparisonType, setComparisonType] = useState<ComparisonType>("machine_vs_machine");
  const [viewState, setViewState] = useState<ViewState>("form");
  const [reportId, setReportId] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<{ error_code: string; error_message: string } | null>(null);

  const [deviceA, setDeviceA] = useState<string>("");
  const [deviceB, setDeviceB] = useState<string>("");
  const [deviceSingle, setDeviceSingle] = useState<string>("");

  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  const [periodAStart, setPeriodAStart] = useState<string>("");
  const [periodAEnd, setPeriodAEnd] = useState<string>("");
  const [periodBStart, setPeriodBStart] = useState<string>("");
  const [periodBEnd, setPeriodBEnd] = useState<string>("");

  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function fetchDevices() {
      try {
        const data = await getDevices();
        setDevices(data);
      } catch (err) {
        console.error("Failed to fetch devices:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchDevices();
  }, []);

  const handleRangeChange = useCallback((start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  }, []);

  const handlePeriodAChange = useCallback((start: string, end: string) => {
    setPeriodAStart(start);
    setPeriodAEnd(end);
  }, []);

  const handlePeriodBChange = useCallback((start: string, end: string) => {
    setPeriodBStart(start);
    setPeriodBEnd(end);
  }, []);

  const getPeriodDays = (start: string, end: string): number => {
    if (!start || !end) return 0;
    const diff = new Date(end).getTime() - new Date(start).getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24)) + 1;
  };

  const periodADays = getPeriodDays(periodAStart, periodAEnd);
  const periodBDays = getPeriodDays(periodBStart, periodBEnd);
  const periodsEqual = periodADays > 0 && periodBDays > 0 && periodADays === periodBDays;

  const isFormValid = (() => {
    if (comparisonType === "machine_vs_machine") {
      return deviceA && deviceB && deviceA !== deviceB && startDate && endDate;
    } else {
      return deviceSingle && periodAStart && periodAEnd && periodBStart && periodBEnd && periodsEqual;
    }
  })();

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);

    try {
      const params: ComparisonReportParams = {
        tenant_id: DEFAULT_TENANT_ID,
        comparison_type: comparisonType,
      };

      if (comparisonType === "machine_vs_machine") {
        params.machine_a_id = deviceA;
        params.machine_b_id = deviceB;
        params.start_date = startDate;
        params.end_date = endDate;
      } else {
        params.device_id = deviceSingle;
        params.period_a_start = periodAStart;
        params.period_a_end = periodAEnd;
        params.period_b_start = periodBStart;
        params.period_b_end = periodBEnd;
      }

      const response = await submitComparisonReport(params);
      setReportId(response.report_id);
      setViewState("processing");
    } catch (err) {
      setError({
        error_code: "SUBMIT_ERROR",
        error_message: err instanceof Error ? err.message : "Failed to submit comparison",
      });
      setViewState("failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleComplete = (reportResult: unknown) => {
    setResult(reportResult);
    setViewState("completed");
  };

  const handleError = (err: { error_code: string; error_message: string }) => {
    setError(err);
    setViewState("failed");
  };

  const handleRetry = () => {
    setViewState("form");
    setReportId(null);
    setResult(null);
    setError(null);
  };

  const handleDownload = async () => {
    if (!reportId) return;
    try {
      const blob = await getReportDownload(reportId, DEFAULT_TENANT_ID);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `comparison_report_${reportId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Failed to download report:", err);
      alert("Failed to download report. Please try again.");
    }
  };

  if (loading) {
    return <div className="p-6 text-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Comparative Analysis</h1>
        <p className="text-gray-600 mt-1">Compare energy usage between machines or periods</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          {viewState === "form" && (
            <>
              <div className="bg-white p-4 rounded-lg border">
                <h3 className="font-medium text-gray-900 mb-3">Comparison Type</h3>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="comparisonType"
                      value="machine_vs_machine"
                      checked={comparisonType === "machine_vs_machine"}
                      onChange={() => setComparisonType("machine_vs_machine")}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Machine vs Machine</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="comparisonType"
                      value="period_vs_period"
                      checked={comparisonType === "period_vs_period"}
                      onChange={() => setComparisonType("period_vs_period")}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Period vs Period</span>
                  </label>
                </div>
              </div>

              {comparisonType === "machine_vs_machine" ? (
                <>
                  <div className="bg-white p-4 rounded-lg border">
                    <h3 className="font-medium text-gray-900 mb-3">Select Devices</h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm text-gray-600 mb-1">Device A</label>
                        <select
                          value={deviceA}
                          onChange={(e) => setDeviceA(e.target.value)}
                          className="w-full px-3 py-2 border rounded-md text-sm"
                        >
                          <option value="">Select device...</option>
                          {devices.map((d) => (
                            <option key={d.id} value={d.id}>
                              {d.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-gray-600 mb-1">Device B</label>
                        <select
                          value={deviceB}
                          onChange={(e) => setDeviceB(e.target.value)}
                          className="w-full px-3 py-2 border rounded-md text-sm"
                        >
                          <option value="">Select device...</option>
                          {devices
                            .filter((d) => d.id !== deviceA)
                            .map((d) => (
                              <option key={d.id} value={d.id}>
                                {d.name}
                              </option>
                            ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white p-4 rounded-lg border">
                    <h3 className="font-medium text-gray-900 mb-3">Date Range</h3>
                    <DateRangeSelector
                      onRangeChange={handleRangeChange}
                      disabled={submitting}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-white p-4 rounded-lg border">
                    <h3 className="font-medium text-gray-900 mb-3">Select Device</h3>
                    <select
                      value={deviceSingle}
                      onChange={(e) => setDeviceSingle(e.target.value)}
                      className="w-full px-3 py-2 border rounded-md text-sm"
                    >
                      <option value="">Select device...</option>
                      {devices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="bg-white p-4 rounded-lg border">
                    <h3 className="font-medium text-gray-900 mb-3">Period A</h3>
                    <DateRangeSelector
                      onRangeChange={handlePeriodAChange}
                      disabled={submitting}
                    />
                  </div>

                  <div className="bg-white p-4 rounded-lg border">
                    <h3 className="font-medium text-gray-900 mb-3">Period B</h3>
                    <DateRangeSelector
                      onRangeChange={handlePeriodBChange}
                      disabled={submitting}
                    />
                  </div>

                  {periodADays > 0 && periodBDays > 0 && !periodsEqual && (
                    <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg text-sm text-yellow-800">
                      Warning: Periods must be equal length for fair comparison (A: {periodADays} days, B: {periodBDays} days)
                    </div>
                  )}
                </>
              )}

              <button
                onClick={handleSubmit}
                disabled={!isFormValid || submitting}
                className={`w-full py-3 rounded-lg font-medium transition-colors ${
                  isFormValid && !submitting
                    ? "bg-green-600 text-white hover:bg-green-700"
                    : "bg-gray-200 text-gray-500 cursor-not-allowed"
                }`}
              >
                {submitting ? "Submitting..." : "Generate Comparison"}
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
          {viewState === "form" && (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p>Configure comparison and click Generate</p>
            </div>
          )}

          {viewState === "completed" && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">Comparison Complete</div>
                <p className="text-gray-600 mt-1">Results are ready</p>
              </div>

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
