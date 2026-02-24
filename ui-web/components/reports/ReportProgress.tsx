"use client";

import { useState, useEffect, useCallback } from "react";
import { getReportStatus, getReportResult, ReportStatus } from "@/lib/reportApi";

interface ReportProgressProps {
  reportId: string;
  tenantId: string;
  onComplete: (result: unknown) => void;
  onError: (error: { error_code: string; error_message: string }) => void;
}

export function ReportProgress({
  reportId,
  tenantId,
  onComplete,
  onError,
}: ReportProgressProps) {
  const [status, setStatus] = useState<ReportStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const checkStatus = useCallback(async () => {
    try {
      const data = await getReportStatus(reportId, tenantId);
      setStatus(data);

      if (data.status === "completed") {
        const result = await getReportResult(reportId, tenantId);
        onComplete(result);
      } else if (data.status === "failed") {
        onError({
          error_code: data.error_code || "UNKNOWN_ERROR",
          error_message: data.error_message || "Report generation failed",
        });
      }
    } catch (error) {
      console.error("Failed to check report status:", error);
    }
  }, [reportId, tenantId, onComplete, onError]);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, [checkStatus]);

  if (!status) {
    return (
      <div className="text-center py-8 text-gray-500">Loading...</div>
    );
  }

  const statusMessages: Record<string, string> = {
    pending: "Report queued...",
    processing: "Processing report...",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">
          {statusMessages[status.status] || status.status}
        </span>
        <span className="text-sm text-gray-500">{status.progress}%</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${status.progress}%` }}
        />
      </div>

      {status.status === "processing" && (
        <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Processing...
        </div>
      )}
    </div>
  );
}
