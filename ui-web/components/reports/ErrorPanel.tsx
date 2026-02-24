"use client";

interface ErrorPanelProps {
  errorCode: string;
  errorMessage: string;
  onRetry: () => void;
}

const errorMessages: Record<string, string> = {
  DEVICE_NOT_FOUND: "Device not found. Check device configuration.",
  NO_TELEMETRY_DATA: "No data in selected date range. Try a different period.",
  INSUFFICIENT_TELEMETRY_DATA: "Device telemetry missing required fields (power or voltage/current).",
  TARIFF_NOT_CONFIGURED: "Energy cost not available. Configure tariff in Settings.",
  INVALID_DATE_RANGE: "Invalid date range. Select 1–90 days within the last year.",
  UNKNOWN_ERROR: "An unexpected error occurred. Please try again.",
};

export function ErrorPanel({ errorCode, errorMessage, onRetry }: ErrorPanelProps) {
  const displayMessage = errorMessages[errorCode] || errorMessage;

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-800">Error: {errorCode}</h3>
          <p className="mt-1 text-sm text-red-700">{displayMessage}</p>
          <div className="mt-3">
            <button
              onClick={onRetry}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
