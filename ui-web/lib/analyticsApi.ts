// import { ANALYTICS_SERVICE_BASE } from "./api";

// /* ------------------ types ------------------ */

// export type AnalyticsType =
//   | "anomaly"
//   | "prediction"
//   | "forecast";

// export interface RunAnalyticsRequest {
//   device_id: string;
//   analysis_type: AnalyticsType;
//   model_name: string;

//   // explicit dataset selected from UI
//   dataset_key?: string;

//   // backward compatibility
//   date_range_start?: string;
//   date_range_end?: string;
// }

// export interface AvailableDataset {
//   key: string;
//   size: number;
//   last_modified: string;
// }

// export interface AvailableDatasetsResponse {
//   device_id: string;
//   datasets: AvailableDataset[];
// }

// /* ------------------ APIs ------------------ */

// export async function runAnalytics(payload: RunAnalyticsRequest) {
//   const res = await fetch(
//     `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/run`,
//     {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify(payload),
//     }
//   );

//   if (!res.ok) {
//     throw new Error(`HTTP ${res.status}`);
//   }

//   return res.json();
// }

// export async function getAnalyticsStatus(jobId: string) {
//   const res = await fetch(
//     `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/status/${jobId}`
//   );

//   if (!res.ok) {
//     throw new Error(`HTTP ${res.status}`);
//   }

//   return res.json();
// }

// export async function getAnalyticsResults(jobId: string) {
//   const res = await fetch(
//     `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/results/${jobId}`
//   );

//   if (!res.ok) {
//     throw new Error(`HTTP ${res.status}`);
//   }

//   return res.json();
// }

// /* ------------------ models ------------------ */

// export async function getSupportedModels(): Promise<string[]> {
//   const res = await fetch(
//     `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/models`
//   );

//   if (!res.ok) {
//     throw new Error(`HTTP ${res.status}`);
//   }

//   const json = await res.json();

//   /*
//     Your backend currently returns a structured object
//     (SupportedModelsResponse):

//       {
//         anomaly_detection: [...],
//         failure_prediction: [...],
//         forecasting: [...]
//       }

//     For the device analytics page we only allow anomaly for now.
//   */

//   if (json?.anomaly_detection && Array.isArray(json.anomaly_detection)) {
//     return json.anomaly_detection;
//   }

//   throw new Error("Invalid models response from analytics service");
// }

// /* ------------------ datasets ------------------ */

// export async function getAvailableDatasets(
//   deviceId: string
// ): Promise<AvailableDatasetsResponse> {

//   const res = await fetch(
//     `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/datasets?device_id=${deviceId}`
//   );

//   if (!res.ok) {
//     throw new Error(`HTTP ${res.status}`);
//   }

//   const json = await res.json();

//   if (!Array.isArray(json?.datasets)) {
//     throw new Error("Invalid datasets response from analytics service");
//   }

//   return json;
// }



import { ANALYTICS_SERVICE_BASE } from "./api";

/* ------------------ types ------------------ */

export type AnalyticsType = "anomaly" | "prediction" | "forecast";

export interface RunAnalyticsRequest {
  device_id: string;
  analysis_type: AnalyticsType;
  model_name: string;
  dataset_key?: string;
}

export interface AvailableDataset {
  key: string;
  size: number;
  last_modified: string;
}

export interface AvailableDatasetsResponse {
  device_id: string;
  datasets: AvailableDataset[];
}

/* ------------------ supported models ------------------ */

export interface SupportedModelsResponse {
  anomaly_detection: string[];
  failure_prediction: string[];
  forecasting: string[];
}

/* ------------------ APIs ------------------ */

export async function runAnalytics(payload: RunAnalyticsRequest) {
  const res = await fetch(
    `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/run`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getAnalyticsStatus(jobId: string) {
  const res = await fetch(
    `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/status/${jobId}`
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getAnalyticsResults(jobId: string) {
  const res = await fetch(
    `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/results/${jobId}`
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

/* ------------------ models ------------------ */

export async function getSupportedModels(): Promise<SupportedModelsResponse> {
  const res = await fetch(
    `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/models`
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const json = await res.json();

  if (
    !json ||
    !Array.isArray(json.anomaly_detection) ||
    !Array.isArray(json.failure_prediction) ||
    !Array.isArray(json.forecasting)
  ) {
    throw new Error("Invalid models response from analytics service");
  }

  return json;
}

/* ------------------ datasets ------------------ */

export async function getAvailableDatasets(
  deviceId: string
): Promise<AvailableDatasetsResponse> {
  const res = await fetch(
    `${ANALYTICS_SERVICE_BASE}/api/v1/analytics/datasets?device_id=${deviceId}`
  );

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const json = await res.json();

  if (!Array.isArray(json?.datasets)) {
    throw new Error("Invalid datasets response from analytics service");
  }

  return json;
}