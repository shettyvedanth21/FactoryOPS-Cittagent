// "use client";

// import { useEffect, useState } from "react";
// import {
//   runAnalytics,
//   getAnalyticsStatus,
//   getAnalyticsResults,
//   getSupportedModels,
//   getAvailableDatasets,
//   SupportedModelsResponse,
//   AvailableDatasetsResponse,
//   AnalyticsType,
// } from "@/lib/analyticsApi";
// import { getDevices, Device } from "@/lib/deviceApi";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Select } from "@/components/ui/input";
// import { Badge } from "@/components/ui/badge";
// import { AnomalyChart, ForecastChart } from "@/components/charts/telemetry-charts";

// export default function AnalyticsPage() {
//   const [devices, setDevices] = useState<Device[]>([]);
//   const [selectedDevice, setSelectedDevice] = useState<string>("");
//   const [analysisType, setAnalysisType] = useState<AnalyticsType>("anomaly");
//   const [modelName, setModelName] = useState<string>("");
//   const [models, setModels] = useState<SupportedModelsResponse | null>(null);
//   const [datasets, setDatasets] = useState<AvailableDatasetsResponse | null>(null);
//   const [selectedDataset, setSelectedDataset] = useState<string>("");
  
//   const [jobId, setJobId] = useState<string | null>(null);
//   const [status, setStatus] = useState<string | null>(null);
//   const [results, setResults] = useState<any>(null);
  
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState<string | null>(null);
//   const [initialLoading, setInitialLoading] = useState(true);

//   // Load initial data
//   useEffect(() => {
//     const loadInitialData = async () => {
//       try {
//         const [devicesData, modelsData] = await Promise.all([
//           getDevices(),
//           getSupportedModels(),
//         ]);
//         setDevices(devicesData);
//         setModels(modelsData);
//         if (devicesData.length > 0) {
//           setSelectedDevice(devicesData[0].id);
//         }
//         if (modelsData.anomaly_detection.length > 0) {
//           setModelName(modelsData.anomaly_detection[0]);
//         }
//       } catch (err) {
//         setError(err instanceof Error ? err.message : "Failed to load initial data");
//       } finally {
//         setInitialLoading(false);
//       }
//     };

//     loadInitialData();
//   }, []);

//   // Load datasets when device changes
//   useEffect(() => {
//     if (!selectedDevice) return;
    
//     getAvailableDatasets(selectedDevice)
//       .then((data) => {
//         setDatasets(data);
//         if (data.datasets.length > 0) {
//           setSelectedDataset(data.datasets[0].key);
//         }
//       })
//       .catch((err) => console.error("Failed to load datasets:", err));
//   }, [selectedDevice]);

//   // Update model when analysis type changes
//   useEffect(() => {
//     if (!models) return;
    
//     const modelList =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;
    
//     setModelName(modelList[0] ?? "");
//   }, [analysisType, models]);

//   // Poll job status
//   useEffect(() => {
//     if (!jobId) return;

//     const interval = setInterval(async () => {
//       try {
//         const statusResponse = await getAnalyticsStatus(jobId);
//         setStatus(statusResponse.status);

//         if (statusResponse.status === "completed") {
//           clearInterval(interval);
//           const resultsData = await getAnalyticsResults(jobId);
//           setResults(resultsData);
//         }

//         if (statusResponse.status === "failed") {
//           clearInterval(interval);
//           setError("Analysis failed");
//         }
//       } catch (err: any) {
//         setError(err.message);
//         clearInterval(interval);
//       }
//     }, 2000);

//     return () => clearInterval(interval);
//   }, [jobId]);

//   const handleRun = async () => {
//     setError(null);
//     setResults(null);
//     setStatus(null);

//     if (!modelName) {
//       setError("Please select a model");
//       return;
//     }

//     if (!selectedDataset) {
//       setError("Please select a dataset");
//       return;
//     }

//     try {
//       setLoading(true);

//       const response = await runAnalytics({
//         device_id: selectedDevice,
//         analysis_type: analysisType,
//         model_name: modelName,
//         dataset_key: selectedDataset,
//       });

//       setJobId(response.job_id);
//       setStatus(response.status);
//     } catch (err: any) {
//       setError(err.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   const getModelOptions = () => {
//     if (!models) return [];
    
//     const modelList =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;
    
//     return modelList.map((m) => ({ value: m, label: m }));
//   };

//   const formatBytes = (bytes: number) => {
//     if (bytes === 0) return "0 B";
//     const k = 1024;
//     const sizes = ["B", "KB", "MB", "GB"];
//     const i = Math.floor(Math.log(bytes) / Math.log(k));
//     return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
//   };

//   if (initialLoading) {
//     return (
//       <div className="p-8">
//         <div className="flex items-center justify-center h-64">
//           <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
//         </div>
//       </div>
//     );
//   }

//   return (
//     <div className="p-8">
//       <div className="max-w-7xl mx-auto space-y-6">
//         {/* Header */}
//         <div>
//           <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
//           <p className="text-slate-500 mt-1">
//             Run AI-powered analytics on your machine data
//           </p>
//         </div>

//         {/* Configuration Card */}
//         <Card>
//           <CardHeader>
//             <CardTitle>Analysis Configuration</CardTitle>
//           </CardHeader>
//           <CardContent>
//             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
//               <Select
//                 label="Machine"
//                 value={selectedDevice}
//                 onChange={(e) => setSelectedDevice(e.target.value)}
//                 options={devices.map((d) => ({ value: d.id, label: d.name }))}
//               />
              
//               <Select
//                 label="Analysis Type"
//                 value={analysisType}
//                 onChange={(e) => setAnalysisType(e.target.value as AnalyticsType)}
//                 options={[
//                   { value: "anomaly", label: "Anomaly Detection" },
//                   { value: "prediction", label: "Failure Prediction" },
//                   { value: "forecast", label: "Forecast" },
//                 ]}
//               />
              
//               <Select
//                 label="Model"
//                 value={modelName}
//                 onChange={(e) => setModelName(e.target.value)}
//                 options={getModelOptions()}
//               />
              
//               <Select
//                 label="Dataset"
//                 value={selectedDataset}
//                 onChange={(e) => setSelectedDataset(e.target.value)}
//                 options={datasets?.datasets.map((d) => ({
//                   value: d.key,
//                   label: `${d.key} (${formatBytes(d.size)})`,
//                 })) || []}
//               />
//             </div>
            
//             <div className="mt-6 flex items-center gap-4">
//               <Button
//                 onClick={handleRun}
//                 isLoading={loading}
//                 disabled={loading || status === "running"}
//               >
//                 {status === "running" ? "Running..." : "Create Model & Start Training"}
//               </Button>
              
//               {status && (
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status}
//                 </Badge>
//               )}
//             </div>
            
//             {error && (
//               <p className="mt-4 text-sm text-red-600">{error}</p>
//             )}
//           </CardContent>
//         </Card>

//         {/* Job Status */}
//         {jobId && (
//           <Card>
//             <CardHeader>
//               <CardTitle>Job Status</CardTitle>
//             </CardHeader>
//             <CardContent>
//               <div className="space-y-2 text-sm">
//                 <p>
//                   <span className="text-slate-500">Job ID:</span>{" "}
//                   <span className="font-mono">{jobId}</span>
//                 </p>
//                 <p>
//                   <span className="text-slate-500">Status:</span>{" "}
//                   <Badge
//                     variant={
//                       status === "completed"
//                         ? "success"
//                         : status === "failed"
//                         ? "error"
//                         : "info"
//                     }
//                   >
//                     {status || "pending"}
//                   </Badge>
//                 </p>
//               </div>
//             </CardContent>
//           </Card>
//         )}

//         {/* Results */}
//         {results && (
//           <div className="space-y-6">
//             <Card>
//               <CardHeader>
//                 <CardTitle>Analysis Results</CardTitle>
//               </CardHeader>
//               <CardContent>
//                 {/* Metrics */}
//                 {results.metrics && (
//                   <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
//                     {results.metrics.accuracy !== undefined && (
//                       <div className="bg-slate-50 rounded-lg p-4">
//                         <p className="text-sm text-slate-500">Accuracy</p>
//                         <p className="text-2xl font-bold text-slate-900">
//                           {(results.metrics.accuracy * 100).toFixed(1)}%
//                         </p>
//                       </div>
//                     )}
//                     {results.metrics.total_anomalies !== undefined && (
//                       <div className="bg-slate-50 rounded-lg p-4">
//                         <p className="text-sm text-slate-500">Total Anomalies</p>
//                         <p className="text-2xl font-bold text-slate-900">
//                           {results.metrics.total_anomalies}
//                         </p>
//                       </div>
//                     )}
//                     {results.metrics.confidence !== undefined && (
//                       <div className="bg-slate-50 rounded-lg p-4">
//                         <p className="text-sm text-slate-500">Confidence</p>
//                         <p className="text-2xl font-bold text-slate-900">
//                           {(results.metrics.confidence * 100).toFixed(1)}%
//                         </p>
//                       </div>
//                     )}
//                   </div>
//                 )}

//                 {/* Charts */}
//                 {results.data && results.data.length > 0 && (
//                   <div className="space-y-6">
//                     {analysisType === "anomaly" && (
//                       <AnomalyChart
//                         data={results.data.map((d: any) => ({
//                           timestamp: d.timestamp,
//                           value: d.value,
//                           isAnomaly: d.is_anomaly,
//                           anomalyScore: d.anomaly_score,
//                         }))}
//                         title="Anomaly Detection Results"
//                       />
//                     )}
                    
//                     {analysisType === "prediction" && (
//                       <div>
//                         <h4 className="text-sm font-medium text-slate-700 mb-4">
//                           Failure Probability
//                         </h4>
//                         <div className="h-64 bg-slate-50 rounded-lg flex items-center justify-center">
//                           {/* Placeholder for prediction visualization */}
//                           <p className="text-slate-400">Prediction chart would go here</p>
//                         </div>
//                       </div>
//                     )}
                    
//                     {analysisType === "forecast" && (
//                       <ForecastChart
//                         data={results.data.map((d: any) => ({
//                           timestamp: d.timestamp,
//                           actual: d.actual,
//                           forecast: d.forecast,
//                           upperBound: d.upper_bound,
//                           lowerBound: d.lower_bound,
//                         }))}
//                         title="Forecast Results"
//                       />
//                     )}
//                   </div>
//                 )}

//                 {/* Raw Results */}
//                 <details className="mt-6">
//                   <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-700">
//                     View Raw Results
//                   </summary>
//                   <pre className="mt-2 bg-slate-900 text-slate-50 p-4 rounded-lg text-xs overflow-auto max-h-96">
//                     {JSON.stringify(results, null, 2)}
//                   </pre>
//                 </details>
//               </CardContent>
//             </Card>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// }








// "use client";

// import { useEffect, useState } from "react";

// import {
//   runAnalytics,
//   getAnalyticsStatus,
//   getAnalyticsResults,
//   getSupportedModels,
//   getAvailableDatasets,
//   SupportedModelsResponse,
//   AvailableDatasetsResponse,
//   AnalyticsType,
// } from "@/lib/analyticsApi";

// import { runExport, getExportStatus } from "@/lib/dataExportApi";

// import { getDevices, Device } from "@/lib/deviceApi";

// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Select } from "@/components/ui/input";
// import { Badge } from "@/components/ui/badge";

// import {
//   AnomalyChart,
//   ForecastChart,
// } from "@/components/charts/telemetry-charts";

// import { AnalysisResults } from "./AnalysisResults";

// export default function AnalyticsPage() {
//   const [devices, setDevices] = useState<Device[]>([]);
//   const [selectedDevice, setSelectedDevice] = useState<string>("");

//   const [analysisType, setAnalysisType] =
//     useState<AnalyticsType>("anomaly");

//   const [modelName, setModelName] = useState<string>("");

//   const [models, setModels] =
//     useState<SupportedModelsResponse | null>(null);

//   const [datasets, setDatasets] =
//     useState<AvailableDatasetsResponse | null>(null);

//   const [selectedDataset, setSelectedDataset] = useState<string>("");

//   const [jobId, setJobId] = useState<string | null>(null);
//   const [status, setStatus] = useState<string | null>(null);
//   const [results, setResults] = useState<any>(null);

//   const [loading, setLoading] = useState(false);
//   const [initialLoading, setInitialLoading] = useState(true);
//   const [error, setError] = useState<string | null>(null);

//   // export state (device scoped – matches your API)
//   const [exportStatus, setExportStatus] = useState<string | null>(null);

//   /* ---------------- initial load ---------------- */

//   useEffect(() => {
//     const load = async () => {
//       try {
//         const [d, m] = await Promise.all([
//           getDevices(),
//           getSupportedModels(),
//         ]);

//         setDevices(d);
//         setModels(m);

//         if (d.length > 0) {
//           setSelectedDevice(d[0].id);
//         }

//         if (m.anomaly_detection.length > 0) {
//           setModelName(m.anomaly_detection[0]);
//         }
//       } catch (e: any) {
//         setError(e.message);
//       } finally {
//         setInitialLoading(false);
//       }
//     };

//     load();
//   }, []);

//   /* ---------------- datasets ---------------- */

//   useEffect(() => {
//     if (!selectedDevice) return;

//     getAvailableDatasets(selectedDevice)
//       .then((d) => {
//         setDatasets(d);
//         if (d.datasets.length > 0) {
//           setSelectedDataset(d.datasets[0].key);
//         }
//       })
//       .catch((e) => {
//         console.error(e);
//       });
//   }, [selectedDevice]);

//   /* ---------------- models by type ---------------- */

//   useEffect(() => {
//     if (!models) return;

//     const list =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;

//     setModelName(list[0] ?? "");
//   }, [analysisType, models]);

//   /* ---------------- analytics polling ---------------- */

//   useEffect(() => {
//     if (!jobId) return;

//     const t = setInterval(async () => {
//       try {
//         const s = await getAnalyticsStatus(jobId);
//         setStatus(s.status);

//         if (s.status === "completed") {
//           clearInterval(t);
//           const r = await getAnalyticsResults(jobId);
//           setResults(r);
//         }

//         if (s.status === "failed") {
//           clearInterval(t);
//           setError("Analysis failed");
//         }
//       } catch (e: any) {
//         clearInterval(t);
//         setError(e.message);
//       }
//     }, 2000);

//     return () => clearInterval(t);
//   }, [jobId]);

//   /* ---------------- export polling (device based) ---------------- */

//   useEffect(() => {
//     if (!exportStatus || !selectedDevice) return;
//     if (exportStatus !== "running") return;

//     const t = setInterval(async () => {
//       try {
//         const s = await getExportStatus(selectedDevice);
//         setExportStatus(s.status);

//         if (s.status === "completed") {
//           clearInterval(t);

//           const d = await getAvailableDatasets(selectedDevice);
//           setDatasets(d);

//           if (d.datasets.length > 0) {
//             setSelectedDataset(d.datasets[0].key);
//           }
//         }

//         if (s.status === "failed") {
//           clearInterval(t);
//         }
//       } catch {
//         clearInterval(t);
//         setExportStatus("failed");
//       }
//     }, 2000);

//     return () => clearInterval(t);
//   }, [exportStatus, selectedDevice]);

//   /* ---------------- handlers ---------------- */

//   const handleRun = async () => {
//     setError(null);
//     setResults(null);
//     setStatus(null);

//     if (!modelName) {
//       setError("Please select a model");
//       return;
//     }

//     if (!selectedDataset) {
//       setError("Please select a dataset");
//       return;
//     }

//     try {
//       setLoading(true);

//       const r = await runAnalytics({
//         device_id: selectedDevice,
//         analysis_type: analysisType,
//         model_name: modelName,
//         dataset_key: selectedDataset,
//       });

//       setJobId(r.job_id);
//       setStatus(r.status);
//     } catch (e: any) {
//       setError(e.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleExportLatest = async () => {
//     try {
//       setExportStatus("running");
//       await runExport(selectedDevice);
//     } catch (e: any) {
//       setExportStatus("failed");
//       setError(e.message || "Export failed");
//     }
//   };

//   const getModelOptions = () => {
//     if (!models) return [];

//     const list =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;

//     return list.map((m) => ({ value: m, label: m }));
//   };

//   const formatBytes = (bytes: number) => {
//     if (bytes === 0) return "0 B";
//     const k = 1024;
//     const sizes = ["B", "KB", "MB", "GB"];
//     const i = Math.floor(Math.log(bytes) / Math.log(k));
//     return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
//   };

//   if (initialLoading) {
//     return (
//       <div className="p-8 flex justify-center">
//         <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
//       </div>
//     );
//   }

//   return (
//     <div className="p-8">
//       <div className="max-w-7xl mx-auto space-y-6">

//         <div>
//           <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
//           <p className="text-slate-500 mt-1">
//             Run AI-powered analytics on your machine data
//           </p>
//         </div>

//         {/* configuration */}

//         <Card>
//           <CardHeader>
//             <CardTitle>Analysis Configuration</CardTitle>
//           </CardHeader>

//           <CardContent>
//             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

//               <Select
//                 label="Machine"
//                 value={selectedDevice}
//                 onChange={(e) => setSelectedDevice(e.target.value)}
//                 options={devices.map((d) => ({
//                   value: d.id,
//                   label: d.name,
//                 }))}
//               />

//               <Select
//                 label="Analysis Type"
//                 value={analysisType}
//                 onChange={(e) =>
//                   setAnalysisType(e.target.value as AnalyticsType)
//                 }
//                 options={[
//                   { value: "anomaly", label: "Anomaly Detection" },
//                   { value: "prediction", label: "Failure Prediction" },
//                   { value: "forecast", label: "Forecast" },
//                 ]}
//               />

//               <Select
//                 label="Model"
//                 value={modelName}
//                 onChange={(e) => setModelName(e.target.value)}
//                 options={getModelOptions()}
//               />

//               <Select
//                 label="Dataset"
//                 value={selectedDataset}
//                 onChange={(e) => setSelectedDataset(e.target.value)}
//                 options={
//                   datasets?.datasets.map((d) => ({
//                     value: d.key,
//                     label: `${d.key} (${formatBytes(d.size)})`,
//                   })) ?? []
//                 }
//               />
//             </div>

//             <div className="mt-6 flex items-center gap-4">

//               <Button
//                 onClick={handleRun}
//                 isLoading={loading}
//                 disabled={loading || status === "running"}
//               >
//                 {status === "running"
//                   ? "Running..."
//                   : "Create Model & Start Training"}
//               </Button>

//               {status && (
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status}
//                 </Badge>
//               )}
//             </div>

//             {error && (
//               <p className="mt-4 text-sm text-red-600">{error}</p>
//             )}
//           </CardContent>
//         </Card>

//         {/* job info */}

//         {jobId && (
//           <Card>
//             <CardHeader>
//               <CardTitle>Job Status</CardTitle>
//             </CardHeader>
//             <CardContent className="text-sm space-y-1">
//               <div>
//                 <span className="text-slate-500">Job ID: </span>
//                 <span className="font-mono">{jobId}</span>
//               </div>
//               <div>
//                 <span className="text-slate-500">Status: </span>
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status ?? "pending"}
//                 </Badge>
//               </div>
//             </CardContent>
//           </Card>
//         )}

//         {/* results */}

//         {results && (
//           <Card>
//             <CardHeader className="flex flex-row items-center justify-between">
//               <CardTitle>Analysis Results</CardTitle>

//               <div className="flex items-center gap-3">
//                 <Button
//                   variant="outline"
//                   size="sm"
//                   onClick={handleExportLatest}
//                   disabled={!selectedDevice || exportStatus === "running"}
//                 >
//                   {exportStatus === "running"
//                     ? "Exporting…"
//                     : "Export latest data"}
//                 </Button>

//                 {exportStatus && (
//                   <Badge
//                     variant={
//                       exportStatus === "completed"
//                         ? "success"
//                         : exportStatus === "failed"
//                         ? "error"
//                         : "info"
//                     }
//                   >
//                     {exportStatus}
//                   </Badge>
//                 )}
//               </div>
//             </CardHeader>

//             <CardContent>

//               {results.metrics && (
//                 <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
//                   {results.metrics.accuracy !== undefined && (
//                     <div className="bg-slate-50 rounded-lg p-4">
//                       <p className="text-sm text-slate-500">Accuracy</p>
//                       <p className="text-2xl font-bold">
//                         {(results.metrics.accuracy * 100).toFixed(1)}%
//                       </p>
//                     </div>
//                   )}

//                   {results.metrics.total_anomalies !== undefined && (
//                     <div className="bg-slate-50 rounded-lg p-4">
//                       <p className="text-sm text-slate-500">
//                         Total Anomalies
//                       </p>
//                       <p className="text-2xl font-bold">
//                         {results.metrics.total_anomalies}
//                       </p>
//                     </div>
//                   )}

//                   {results.metrics.confidence !== undefined && (
//                     <div className="bg-slate-50 rounded-lg p-4">
//                       <p className="text-sm text-slate-500">Confidence</p>
//                       <p className="text-2xl font-bold">
//                         {(results.metrics.confidence * 100).toFixed(1)}%
//                       </p>
//                     </div>
//                   )}
//                 </div>
//               )}

//               {results.data && results.data.length > 0 && (
//                 <div className="space-y-6 mb-6">
//                   {analysisType === "anomaly" && (
//                     <AnomalyChart
//                       data={results.data.map((d: any) => ({
//                         timestamp: d.timestamp,
//                         value: d.value,
//                         isAnomaly: d.is_anomaly,
//                         anomalyScore: d.anomaly_score,
//                       }))}
//                       title="Anomaly Detection Results"
//                     />
//                   )}

//                   {analysisType === "forecast" && (
//                     <ForecastChart
//                       data={results.data.map((d: any) => ({
//                         timestamp: d.timestamp,
//                         actual: d.actual,
//                         forecast: d.forecast,
//                         upperBound: d.upper_bound,
//                         lowerBound: d.lower_bound,
//                       }))}
//                       title="Forecast Results"
//                     />
//                   )}
//                 </div>
//               )}

//               <AnalysisResults
//                 results={results}
//                 analysisType={analysisType}
//               />

//             </CardContent>
//           </Card>
//         )}
//       </div>
//     </div>
//   );
// }













// "use client";

// import { useEffect, useState } from "react";

// import {
//   runAnalytics,
//   getAnalyticsStatus,
//   getAnalyticsResults,
//   getSupportedModels,
//   getAvailableDatasets,
//   SupportedModelsResponse,
//   AvailableDatasetsResponse,
//   AnalyticsType,
// } from "@/lib/analyticsApi";

// import { runExport, getExportStatus } from "@/lib/dataExportApi";
// import { getDevices, Device } from "@/lib/deviceApi";

// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Select } from "@/components/ui/input";
// import { Badge } from "@/components/ui/badge";

// import { AnalysisResults } from "./AnalysisResults";

// export default function AnalyticsPage() {
//   const [devices, setDevices] = useState<Device[]>([]);
//   const [selectedDevice, setSelectedDevice] = useState("");

//   const [analysisType, setAnalysisType] =
//     useState<AnalyticsType>("anomaly");

//   const [modelName, setModelName] = useState("");

//   const [models, setModels] =
//     useState<SupportedModelsResponse | null>(null);

//   const [datasets, setDatasets] =
//     useState<AvailableDatasetsResponse | null>(null);

//   const [selectedDataset, setSelectedDataset] = useState("");

//   const [jobId, setJobId] = useState<string | null>(null);
//   const [status, setStatus] = useState<string | null>(null);
//   const [results, setResults] = useState<any>(null);

//   const [loading, setLoading] = useState(false);
//   const [initialLoading, setInitialLoading] = useState(true);
//   const [error, setError] = useState<string | null>(null);

//   const [exporting, setExporting] = useState(false);

//   /* ------------------------------------ */
//   /* initial load                          */
//   /* ------------------------------------ */

//   useEffect(() => {
//     const load = async () => {
//       try {
//         const [devicesData, modelsData] = await Promise.all([
//           getDevices(),
//           getSupportedModels(),
//         ]);

//         setDevices(devicesData);
//         setModels(modelsData);

//         if (devicesData.length) {
//           setSelectedDevice(devicesData[0].id);
//         }

//         if (modelsData.anomaly_detection.length) {
//           setModelName(modelsData.anomaly_detection[0]);
//         }
//       } catch (e: any) {
//         setError(e.message);
//       } finally {
//         setInitialLoading(false);
//       }
//     };

//     load();
//   }, []);

//   /* ------------------------------------ */
//   /* load datasets per device              */
//   /* ------------------------------------ */

//   useEffect(() => {
//     if (!selectedDevice) return;

//     getAvailableDatasets(selectedDevice)
//       .then((d) => {
//         setDatasets(d);
//         if (d.datasets.length) {
//           setSelectedDataset(d.datasets[0].key);
//         }
//       })
//       .catch((e) => setError(e.message));
//   }, [selectedDevice]);

//   /* ------------------------------------ */
//   /* model list per type                   */
//   /* ------------------------------------ */

//   useEffect(() => {
//     if (!models) return;

//     const list =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;

//     setModelName(list[0] ?? "");
//   }, [analysisType, models]);

//   /* ------------------------------------ */
//   /* polling                               */
//   /* ------------------------------------ */

//   useEffect(() => {
//     if (!jobId) return;

//     const t = setInterval(async () => {
//       try {
//         const s = await getAnalyticsStatus(jobId);
//         setStatus(s.status);

//         if (s.status === "completed") {
//           clearInterval(t);
//           const r = await getAnalyticsResults(jobId);
//           setResults(r);
//         }

//         if (s.status === "failed") {
//           clearInterval(t);
//           setError("Analysis failed");
//         }
//       } catch (e: any) {
//         clearInterval(t);
//         setError(e.message);
//       }
//     }, 2000);

//     return () => clearInterval(t);
//   }, [jobId]);

//   /* ------------------------------------ */
//   /* run                                  */
//   /* ------------------------------------ */

//   const handleRun = async () => {
//     setError(null);
//     setResults(null);
//     setJobId(null);
//     setStatus(null);

//     if (!selectedDataset || !modelName) return;

//     try {
//       setLoading(true);

//       const r = await runAnalytics({
//         device_id: selectedDevice,
//         analysis_type: analysisType,
//         model_name: modelName,
//         dataset_key: selectedDataset,
//       });

//       setJobId(r.job_id);
//       setStatus(r.status);
//     } catch (e: any) {
//       setError(e.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   /* ------------------------------------ */
//   /* export latest data                    */
//   /* ------------------------------------ */

//   const handleExportLatest = async () => {
//     if (!selectedDevice) return;

//     try {
//       setExporting(true);

//       await runExport(selectedDevice);

//       let finished = false;

//       while (!finished) {
//         await new Promise((r) => setTimeout(r, 2000));
//         const s = await getExportStatus(selectedDevice);

//         if (s.status === "completed") {
//           finished = true;
//         }

//         if (s.status === "failed") {
//           throw new Error("Export failed");
//         }
//       }

//       const updated = await getAvailableDatasets(selectedDevice);
//       setDatasets(updated);

//       if (updated.datasets.length) {
//         setSelectedDataset(updated.datasets[0].key);
//       }
//     } catch (e: any) {
//       setError(e.message);
//     } finally {
//       setExporting(false);
//     }
//   };

//   const getModelOptions = () => {
//     if (!models) return [];

//     const list =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;

//     return list.map((m) => ({ value: m, label: m }));
//   };

//   const formatBytes = (b: number) => {
//     if (!b) return "0 B";
//     const k = 1024;
//     const i = Math.floor(Math.log(b) / Math.log(k));
//     return `${(b / Math.pow(k, i)).toFixed(2)} ${["B","KB","MB","GB"][i]}`;
//   };

//   if (initialLoading) {
//     return (
//       <div className="p-8 flex justify-center">
//         <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
//       </div>
//     );
//   }

//   return (
//     <div className="p-8">
//       <div className="max-w-7xl mx-auto space-y-6">

//         <div>
//           <h1 className="text-2xl font-bold">Analytics</h1>
//           <p className="text-slate-500">
//             Run AI-powered analytics on your machine data
//           </p>
//         </div>

//         {/* ---------------- config ---------------- */}

//         <Card>
//           <CardHeader>
//             <CardTitle>Analysis Configuration</CardTitle>
//           </CardHeader>

//           <CardContent>
//             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

//               <Select
//                 label="Machine"
//                 value={selectedDevice}
//                 onChange={(e) => setSelectedDevice(e.target.value)}
//                 options={devices.map((d) => ({
//                   value: d.id,
//                   label: d.name,
//                 }))}
//               />

//               <Select
//                 label="Analysis Type"
//                 value={analysisType}
//                 onChange={(e) =>
//                   setAnalysisType(e.target.value as AnalyticsType)
//                 }
//                 options={[
//                   { value: "anomaly", label: "Anomaly Detection" },
//                   { value: "prediction", label: "Failure Prediction" },
//                   { value: "forecast", label: "Forecast" },
//                 ]}
//               />

//               <Select
//                 label="Model"
//                 value={modelName}
//                 onChange={(e) => setModelName(e.target.value)}
//                 options={getModelOptions()}
//               />

//               <Select
//                 label="Dataset"
//                 value={selectedDataset}
//                 onChange={(e) => setSelectedDataset(e.target.value)}
//                 options={
//                   datasets?.datasets.map((d) => ({
//                     value: d.key,
//                     label: `${d.key} (${formatBytes(d.size)})`,
//                   })) || []
//                 }
//               />
//             </div>

//             <div className="mt-6 flex gap-4 items-center">
//               <Button
//                 onClick={handleRun}
//                 isLoading={loading}
//                 disabled={loading || status === "running"}
//               >
//                 Create Model & Start Training
//               </Button>

//               {status && (
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status}
//                 </Badge>
//               )}
//             </div>

//             {error && (
//               <p className="mt-4 text-sm text-red-600">{error}</p>
//             )}
//           </CardContent>
//         </Card>

//         {/* ---------------- job ---------------- */}

//         {jobId && (
//           <Card>
//             <CardHeader>
//               <CardTitle>Job Status</CardTitle>
//             </CardHeader>
//             <CardContent className="text-sm space-y-1">
//               <div>
//                 <span className="text-slate-500">Job ID:</span>{" "}
//                 <span className="font-mono">{jobId}</span>
//               </div>
//               <div>
//                 <span className="text-slate-500">Status:</span>{" "}
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status}
//                 </Badge>
//               </div>
//             </CardContent>
//           </Card>
//         )}

//         {/* ---------------- results ---------------- */}

//         {results && (
//           <Card>
//             <CardHeader className="flex flex-row items-center justify-between">
//               <CardTitle>Analysis Results</CardTitle>

//               <Button
//                 variant="outline"
//                 size="sm"
//                 isLoading={exporting}
//                 onClick={handleExportLatest}
//               >
//                 Export latest data
//               </Button>
//             </CardHeader>

//             <CardContent>
//               <AnalysisResults
//                 results={results}
//                 analysisType={analysisType}
//               />
//             </CardContent>
//           </Card>
//         )}

//       </div>
//     </div>
//   );
// }













// "use client";

// import { useEffect, useState } from "react";

// import {
//   runAnalytics,
//   getAnalyticsStatus,
//   getAnalyticsResults,
//   getSupportedModels,
//   getAvailableDatasets,
//   SupportedModelsResponse,
//   AvailableDatasetsResponse,
//   AnalyticsType,
// } from "@/lib/analyticsApi";

// import { runExport, getExportStatus } from "@/lib/dataExportApi";
// import { getDevices, Device } from "@/lib/deviceApi";

// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Select } from "@/components/ui/input";
// import { Badge } from "@/components/ui/badge";

// import { AnalysisResults } from "./AnalysisResults";

// export default function AnalyticsPage() {
//   const [devices, setDevices] = useState<Device[]>([]);
//   const [selectedDevice, setSelectedDevice] = useState("");

//   const [analysisType, setAnalysisType] =
//     useState<AnalyticsType>("anomaly");

//   const [modelName, setModelName] = useState("");

//   const [models, setModels] =
//     useState<SupportedModelsResponse | null>(null);

//   const [datasets, setDatasets] =
//     useState<AvailableDatasetsResponse | null>(null);

//   const [selectedDataset, setSelectedDataset] = useState("");

//   const [jobId, setJobId] = useState<string | null>(null);
//   const [status, setStatus] = useState<string | null>(null);
//   const [results, setResults] = useState<any>(null);

//   const [loading, setLoading] = useState(false);
//   const [initialLoading, setInitialLoading] = useState(true);
//   const [error, setError] = useState<string | null>(null);

//   const [exporting, setExporting] = useState(false);
//   const [exportStatus, setExportStatus] = useState<string | null>(null);

//   /* ---------------- initial load ---------------- */

//   useEffect(() => {
//     const load = async () => {
//       try {
//         const [d, m] = await Promise.all([
//           getDevices(),
//           getSupportedModels(),
//         ]);

//         setDevices(d);
//         setModels(m);

//         if (d.length) setSelectedDevice(d[0].id);
//         if (m.anomaly_detection.length)
//           setModelName(m.anomaly_detection[0]);
//       } catch (e: any) {
//         setError(e.message);
//       } finally {
//         setInitialLoading(false);
//       }
//     };

//     load();
//   }, []);

//   /* ---------------- datasets ---------------- */

//   useEffect(() => {
//     if (!selectedDevice) return;

//     getAvailableDatasets(selectedDevice)
//       .then((d) => {
//         setDatasets(d);
//         if (d.datasets.length)
//           setSelectedDataset(d.datasets[0].key);
//       })
//       .catch((e) => setError(e.message));
//   }, [selectedDevice]);

//   /* ---------------- model list ---------------- */

//   useEffect(() => {
//     if (!models) return;

//     const list =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;

//     setModelName(list[0] ?? "");
//   }, [analysisType, models]);

//   /* ---------------- analytics polling ---------------- */

//   useEffect(() => {
//     if (!jobId) return;

//     const t = setInterval(async () => {
//       try {
//         const s = await getAnalyticsStatus(jobId);
//         setStatus(s.status);

//         if (s.status === "completed") {
//           clearInterval(t);
//           const r = await getAnalyticsResults(jobId);
//           setResults(r);
//         }

//         if (s.status === "failed") {
//           clearInterval(t);
//           setError("Analysis failed");
//         }
//       } catch (e: any) {
//         clearInterval(t);
//         setError(e.message);
//       }
//     }, 2000);

//     return () => clearInterval(t);
//   }, [jobId]);

//   /* ---------------- export polling ---------------- */

//   useEffect(() => {
//     if (!exporting || !selectedDevice) return;

//     const t = setInterval(async () => {
//       try {
//         const s = await getExportStatus(selectedDevice);
//         setExportStatus(s.status);

//         if (s.status === "completed") {
//           clearInterval(t);
//           setExporting(false);

//           const d = await getAvailableDatasets(selectedDevice);
//           setDatasets(d);

//           if (d.datasets.length)
//             setSelectedDataset(d.datasets[0].key);
//         }

//         if (s.status === "failed") {
//           clearInterval(t);
//           setExporting(false);
//         }
//       } catch {
//         clearInterval(t);
//         setExporting(false);
//         setExportStatus("failed");
//       }
//     }, 2000);

//     return () => clearInterval(t);
//   }, [exporting, selectedDevice]);

//   /* ---------------- handlers ---------------- */

//   const handleRun = async () => {
//     setError(null);
//     setResults(null);
//     setStatus(null);
//     setJobId(null);

//     if (!modelName || !selectedDataset) return;

//     try {
//       setLoading(true);

//       const r = await runAnalytics({
//         device_id: selectedDevice,
//         analysis_type: analysisType,
//         model_name: modelName,
//         dataset_key: selectedDataset,
//       });

//       setJobId(r.job_id);
//       setStatus(r.status);
//     } catch (e: any) {
//       setError(e.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleExportLatest = async () => {
//     if (!selectedDevice) return;

//     try {
//       setExportStatus("running");
//       setExporting(true);
//       await runExport(selectedDevice);
//     } catch (e: any) {
//       setExporting(false);
//       setExportStatus("failed");
//       setError(e.message);
//     }
//   };

//   const getModelOptions = () => {
//     if (!models) return [];

//     const list =
//       analysisType === "anomaly"
//         ? models.anomaly_detection
//         : analysisType === "prediction"
//         ? models.failure_prediction
//         : models.forecasting;

//     return list.map((m) => ({ value: m, label: m }));
//   };

//   const formatBytes = (b: number) => {
//     if (!b) return "0 B";
//     const k = 1024;
//     const i = Math.floor(Math.log(b) / Math.log(k));
//     return `${(b / Math.pow(k, i)).toFixed(2)} ${
//       ["B", "KB", "MB", "GB"][i]
//     }`;
//   };

//   if (initialLoading) {
//     return (
//       <div className="p-8 flex justify-center">
//         <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
//       </div>
//     );
//   }

//   return (
//     <div className="p-8">
//       <div className="max-w-7xl mx-auto space-y-6">

//         <div>
//           <h1 className="text-2xl font-bold">Analytics</h1>
//           <p className="text-slate-500">
//             Run AI-powered analytics on your machine data
//           </p>
//         </div>

//         {/* ---------------- configuration ---------------- */}

//         <Card>
//           <CardHeader className="flex flex-row items-center justify-between">
//             <CardTitle>Analysis Configuration</CardTitle>

//             <div className="flex items-center gap-3">
//               <Button
//                 variant="outline"
//                 size="sm"
//                 isLoading={exporting}
//                 onClick={handleExportLatest}
//                 disabled={!selectedDevice}
//               >
//                 Export latest data
//               </Button>

//               {exportStatus && (
//                 <Badge
//                   variant={
//                     exportStatus === "completed"
//                       ? "success"
//                       : exportStatus === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {exportStatus}
//                 </Badge>
//               )}
//             </div>
//           </CardHeader>

//           <CardContent>
//             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

//               <Select
//                 label="Machine"
//                 value={selectedDevice}
//                 onChange={(e) => setSelectedDevice(e.target.value)}
//                 options={devices.map((d) => ({
//                   value: d.id,
//                   label: d.name,
//                 }))}
//               />

//               <Select
//                 label="Analysis Type"
//                 value={analysisType}
//                 onChange={(e) =>
//                   setAnalysisType(e.target.value as AnalyticsType)
//                 }
//                 options={[
//                   { value: "anomaly", label: "Anomaly Detection" },
//                   { value: "prediction", label: "Failure Prediction" },
//                   { value: "forecast", label: "Forecast" },
//                 ]}
//               />

//               <Select
//                 label="Model"
//                 value={modelName}
//                 onChange={(e) => setModelName(e.target.value)}
//                 options={getModelOptions()}
//               />

//               <Select
//                 label="Dataset"
//                 value={selectedDataset}
//                 onChange={(e) => setSelectedDataset(e.target.value)}
//                 options={
//                   datasets?.datasets.map((d) => ({
//                     value: d.key,
//                     label: `${d.key} (${formatBytes(d.size)})`,
//                   })) ?? []
//                 }
//               />
//             </div>

//             <div className="mt-6 flex gap-4 items-center">
//               <Button
//                 onClick={handleRun}
//                 isLoading={loading}
//                 disabled={loading || status === "running"}
//               >
//                 Create Model & Start Training
//               </Button>

//               {status && (
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status}
//                 </Badge>
//               )}
//             </div>

//             {error && (
//               <p className="mt-4 text-sm text-red-600">{error}</p>
//             )}
//           </CardContent>
//         </Card>

//         {/* ---------------- job ---------------- */}

//         {jobId && (
//           <Card>
//             <CardHeader>
//               <CardTitle>Job Status</CardTitle>
//             </CardHeader>
//             <CardContent className="text-sm space-y-1">
//               <div>
//                 <span className="text-slate-500">Job ID:</span>{" "}
//                 <span className="font-mono">{jobId}</span>
//               </div>
//               <div>
//                 <span className="text-slate-500">Status:</span>{" "}
//                 <Badge
//                   variant={
//                     status === "completed"
//                       ? "success"
//                       : status === "failed"
//                       ? "error"
//                       : "info"
//                   }
//                 >
//                   {status}
//                 </Badge>
//               </div>
//             </CardContent>
//           </Card>
//         )}

//         {/* ---------------- results ---------------- */}

//         {results && (
//           <Card>
//             <CardHeader>
//               <CardTitle>Analysis Results</CardTitle>
//             </CardHeader>
//             <CardContent>
//               <AnalysisResults
//                 results={results}
//                 analysisType={analysisType}
//               />
//             </CardContent>
//           </Card>
//         )}

//       </div>
//     </div>
//   );
// }





"use client";

import { useEffect, useState } from "react";

import {
  runAnalytics,
  getAnalyticsStatus,
  getAnalyticsResults,
  getSupportedModels,
  getAvailableDatasets,
  SupportedModelsResponse,
  AvailableDatasetsResponse,
  AnalyticsType,
} from "@/lib/analyticsApi";

import { runExport, getExportStatus } from "@/lib/dataExportApi";
import { getDevices, Device } from "@/lib/deviceApi";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

import { AnalysisResults } from "./AnalysisResults";

export default function AnalyticsPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState("");

  const [analysisType, setAnalysisType] =
    useState<AnalyticsType>("anomaly");

  const [modelName, setModelName] = useState("");

  const [models, setModels] =
    useState<SupportedModelsResponse | null>(null);

  const [datasets, setDatasets] =
    useState<AvailableDatasetsResponse | null>(null);

  const [selectedDataset, setSelectedDataset] = useState("");

  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);

  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  // NEW – store real export response
  const [exportResult, setExportResult] = useState<any | null>(null);

  /* ---------------- initial load ---------------- */

  useEffect(() => {
    const load = async () => {
      try {
        const [devicesData, modelsData] = await Promise.all([
          getDevices(),
          getSupportedModels(),
        ]);

        setDevices(devicesData);
        setModels(modelsData);

        if (devicesData.length) {
          setSelectedDevice(devicesData[0].id);
        }

        if (modelsData.anomaly_detection.length) {
          setModelName(modelsData.anomaly_detection[0]);
        }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setInitialLoading(false);
      }
    };

    load();
  }, []);

  /* ---------------- datasets ---------------- */

  useEffect(() => {
    if (!selectedDevice) return;

    setExportStatus(null);
    setExportResult(null);

    getAvailableDatasets(selectedDevice)
      .then((d) => {
        setDatasets(d);
        if (d.datasets.length) {
          setSelectedDataset(d.datasets[0].key);
        }
      })
      .catch((e) => setError(e.message));
  }, [selectedDevice]);

  /* ---------------- models by type ---------------- */

  useEffect(() => {
    if (!models) return;

    const list =
      analysisType === "anomaly"
        ? models.anomaly_detection
        : analysisType === "prediction"
        ? models.failure_prediction
        : models.forecasting;

    setModelName(list[0] ?? "");
  }, [analysisType, models]);

  /* ---------------- analytics polling ---------------- */

  useEffect(() => {
    if (!jobId) return;

    const t = setInterval(async () => {
      try {
        const s = await getAnalyticsStatus(jobId);
        setStatus(s.status);

        if (s.status === "completed") {
          clearInterval(t);
          const r = await getAnalyticsResults(jobId);
          setResults(r);
        }

        if (s.status === "failed") {
          clearInterval(t);
          setError("Analysis failed");
        }
      } catch (e: any) {
        clearInterval(t);
        setError(e.message);
      }
    }, 2000);

    return () => clearInterval(t);
  }, [jobId]);

  /* ---------------- run ---------------- */

  const handleRun = async () => {
    setError(null);
    setResults(null);
    setJobId(null);
    setStatus(null);

    if (!selectedDataset || !modelName) return;

    try {
      setLoading(true);

      const r = await runAnalytics({
        device_id: selectedDevice,
        analysis_type: analysisType,
        model_name: modelName,
        dataset_key: selectedDataset,
      });

      setJobId(r.job_id);
      setStatus(r.status);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  /* ---------------- export latest data ---------------- */

  const handleExportLatest = async () => {
    if (!selectedDevice) return;

    try {
      setError(null);
      setExporting(true);
      setExportStatus("running");
      setExportResult(null);

      await runExport(selectedDevice);

      let finished = false;

      while (!finished) {
        await new Promise((r) => setTimeout(r, 2000));

        const s = await getExportStatus(selectedDevice);

        if (s?.status === "completed") {
          finished = true;
          setExportStatus("completed");
          setExportResult(s);
        }

        if (s?.status === "failed") {
          throw new Error("Export failed");
        }
      }

      const updated = await getAvailableDatasets(selectedDevice);
      setDatasets(updated);

      if (updated.datasets.length) {
        setSelectedDataset(updated.datasets[0].key);
      }
    } catch (e: any) {
      setExportStatus("failed");
      setError(e.message);
    } finally {
      setExporting(false);
    }
  };

  const getModelOptions = () => {
    if (!models) return [];

    const list =
      analysisType === "anomaly"
        ? models.anomaly_detection
        : analysisType === "prediction"
        ? models.failure_prediction
        : models.forecasting;

    return list.map((m) => ({ value: m, label: m }));
  };

  const formatBytes = (b: number) => {
    if (!b) return "0 B";
    const k = 1024;
    const i = Math.floor(Math.log(b) / Math.log(k));
    return `${(b / Math.pow(k, i)).toFixed(2)} ${["B", "KB", "MB", "GB"][i]}`;
  };

  if (initialLoading) {
    return (
      <div className="p-8 flex justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-slate-500">
            Run AI-powered analytics on your machine data
          </p>
        </div>

        {/* ---------------- config ---------------- */}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Analysis Configuration</CardTitle>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                isLoading={exporting}
                onClick={handleExportLatest}
                disabled={!selectedDevice || exporting}
              >
                Export latest data
              </Button>

              {exportStatus && (
                <Badge
                  variant={
                    exportStatus === "completed"
                      ? "success"
                      : exportStatus === "failed"
                      ? "error"
                      : "info"
                  }
                >
                  {exportStatus}
                </Badge>
              )}
            </div>
          </CardHeader>

          <CardContent>

            {exportResult && (
              <div className="mb-4 text-sm text-slate-600 space-y-1">
                <div>
                  <span className="text-slate-500">Latest file:</span>{" "}
                  <span className="font-mono">
                    {exportResult.s3_key}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Records:</span>{" "}
                  {exportResult.record_count}
                </div>
                <div>
                  <span className="text-slate-500">Updated at:</span>{" "}
                  {new Date(exportResult.updated_at).toLocaleString()}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

              <Select
                label="Machine"
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                options={devices.map((d) => ({
                  value: d.id,
                  label: d.name,
                }))}
              />

              <Select
                label="Analysis Type"
                value={analysisType}
                onChange={(e) =>
                  setAnalysisType(e.target.value as AnalyticsType)
                }
                options={[
                  { value: "anomaly", label: "Anomaly Detection" },
                  { value: "prediction", label: "Failure Prediction" },
                  { value: "forecast", label: "Forecast" },
                ]}
              />

              <Select
                label="Model"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                options={getModelOptions()}
              />

              <Select
                label="Dataset"
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                options={
                  datasets?.datasets.map((d) => ({
                    value: d.key,
                    label: `${d.key} (${formatBytes(d.size)})`,
                  })) || []
                }
              />
            </div>

            <div className="mt-6 flex gap-4 items-center">
              <Button
                onClick={handleRun}
                isLoading={loading}
                disabled={loading || status === "running"}
              >
                Create Model & Start Training
              </Button>

              {status && (
                <Badge
                  variant={
                    status === "completed"
                      ? "success"
                      : status === "failed"
                      ? "error"
                      : "info"
                  }
                >
                  {status}
                </Badge>
              )}
            </div>

            {error && (
              <p className="mt-4 text-sm text-red-600">{error}</p>
            )}
          </CardContent>
        </Card>

        {/* ---------------- job ---------------- */}

        {jobId && (
          <Card>
            <CardHeader>
              <CardTitle>Job Status</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <div>
                <span className="text-slate-500">Job ID:</span>{" "}
                <span className="font-mono">{jobId}</span>
              </div>
              <div>
                <span className="text-slate-500">Status:</span>{" "}
                <Badge
                  variant={
                    status === "completed"
                      ? "success"
                      : status === "failed"
                      ? "error"
                      : "info"
                  }
                >
                  {status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ---------------- results ---------------- */}

        {results && (
          <Card>
            <CardHeader>
              <CardTitle>Analysis Results</CardTitle>
            </CardHeader>

            <CardContent>
              <AnalysisResults
                results={results}
                analysisType={analysisType}
              />
            </CardContent>
          </Card>
        )}

      </div>
    </div>
  );
}