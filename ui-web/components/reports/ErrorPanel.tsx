"use client";

interface ErrorPanelProps {
  errorCode: string;
  errorMessage: string;
  onRetry: () => void;
}

const errorMessages: Record<string, string> = {
  DEVICE_NOT_FOUND: "Device not found. Please check device configuration.",
  NO_TELEMETRY_DATA: "No telemetry data available for this device in the selected period. The device may not be connected or no data has been transmitted yet. Please ensure the device is operational and try a different date range.",
  INSUFFICIENT_TELEMETRY_DATA: "Incomplete telemetry data. This device is missing required power readings (voltage, current, or power_factor). Energy reports require power monitoring equipment to be properly configured.",
  TARIFF_NOT_CONFIGURED: "Energy cost is not available. Please configure the tariff rates in Settings to see cost estimates.",
  INVALID_DATE_RANGE: "Invalid date range. Please select a date range between 1-90 days within the last year.",
  INVALID_DEVICE_TYPE: "This device does not support energy reports. Please select a power meter device (meter, power_meter, or energy_meter) for energy reports.",
  UNKNOWN_ERROR: "An unexpected error occurred. Please try again later.",
};

export function ErrorPanel({ errorCode, errorMessage, onRetry }: ErrorPanelProps) {
  const displayMessage = errorMessages[errorCode] || errorMessage;
  const isDataError = errorCode === "NO_TELEMETRY_DATA" || errorCode === "INSUFFICIENT_TELEMETRY_DATA";
  
  return (
    <div className={`border rounded-lg p-4 ${isDataError ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          {isDataError ? (
            <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          )}
        </div>
        <div className="flex-1">
          <h3 className={`text-sm font-medium ${isDataError ? 'text-amber-800' : 'text-red-800'}`}>
            {isDataError ? 'Data Not Available' : `Error: ${errorCode}`}
          </h3>
          <p className={`mt-1 text-sm ${isDataError ? 'text-amber-700' : 'text-red-700'}`}>{displayMessage}</p>
          <div className="mt-3">
            <button
              onClick={onRetry}
              className={`inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md ${isDataError ? 'text-amber-700 bg-amber-100 hover:bg-amber-200' : 'text-red-700 bg-red-100 hover:bg-red-200'}`}
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
