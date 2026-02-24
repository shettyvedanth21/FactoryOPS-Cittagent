"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getReportHistory, ReportHistoryItem, getSchedules, deleteSchedule, createSchedule, ScheduleListItem, ScheduleParams } from "@/lib/reportApi";
import { getDevices, Device } from "@/lib/deviceApi";

const DEFAULT_TENANT_ID = "tenant1";

type TabType = "history" | "schedules";

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("history");
  const [history, setHistory] = useState<ReportHistoryItem[]>([]);
  const [schedules, setSchedules] = useState<ScheduleListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const [formData, setFormData] = useState<{
    report_type: "consumption" | "comparison";
    frequency: "daily" | "weekly" | "monthly";
    device_ids: string[];
    group_by: "daily" | "weekly";
  }>({
    report_type: "consumption",
    frequency: "daily",
    device_ids: [],
    group_by: "daily",
  });

  useEffect(() => {
    async function fetchData() {
      try {
        const [historyData, schedulesData, devicesData] = await Promise.all([
          getReportHistory(DEFAULT_TENANT_ID, { limit: 10 }),
          getSchedules(DEFAULT_TENANT_ID),
          getDevices(),
        ]);
        setHistory(historyData.reports);
        setSchedules(schedulesData.schedules);
        setDevices(devicesData);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleCreateSchedule = async () => {
    if (formData.device_ids.length === 0) {
      showToast("Please select at least one device", "error");
      return;
    }

    setSubmitting(true);
    try {
      const params: ScheduleParams = {
        report_type: formData.report_type,
        frequency: formData.frequency,
        params_template: {
          device_ids: formData.device_ids,
          group_by: formData.group_by,
        },
      };
      await createSchedule(DEFAULT_TENANT_ID, params);
      const schedulesData = await getSchedules(DEFAULT_TENANT_ID);
      setSchedules(schedulesData.schedules);
      setShowModal(false);
      setFormData({
        report_type: "consumption",
        frequency: "daily",
        device_ids: [],
        group_by: "daily",
      });
      showToast("Schedule created successfully", "success");
    } catch (error) {
      console.error("Failed to create schedule:", error);
      showToast("Failed to create schedule", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    if (!confirm("Are you sure you want to deactivate this schedule?")) return;
    
    try {
      await deleteSchedule(scheduleId, DEFAULT_TENANT_ID);
      const schedulesData = await getSchedules(DEFAULT_TENANT_ID);
      setSchedules(schedulesData.schedules);
      showToast("Schedule deactivated", "success");
    } catch (error) {
      console.error("Failed to delete schedule:", error);
      showToast("Failed to deactivate schedule", "error");
    }
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-gray-100 text-gray-800",
      processing: "bg-blue-100 text-blue-800",
      completed: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
      skipped: "bg-yellow-100 text-yellow-800",
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status] || styles.pending}`}>
        {status || "pending"}
      </span>
    );
  };

  return (
    <div className="p-6 space-y-8">
      {toast && (
        <div className={`fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 ${
          toast.type === "success" ? "bg-green-600" : "bg-red-600"
        } text-white`}>
          {toast.message}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-600 mt-1">Generate and analyze energy reports</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Link
          href="/reports/energy"
          className="block p-6 bg-white border rounded-xl hover:shadow-lg transition-shadow"
        >
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Energy Consumption Report</h2>
          <p className="text-sm text-gray-600 mt-1">
            kWh breakdown, demand analysis, load factor, cost estimation
          </p>
          <button className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
            Generate Report
          </button>
        </Link>

        <Link
          href="/reports/compare"
          className="block p-6 bg-white border rounded-xl hover:shadow-lg transition-shadow"
        >
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Comparative Analysis</h2>
          <p className="text-sm text-gray-600 mt-1">
            Machine vs Machine or Period vs Period comparison
          </p>
          <button className="mt-4 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700">
            Compare Now
          </button>
        </Link>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab("history")}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === "history"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Report History
          </button>
          <button
            onClick={() => setActiveTab("schedules")}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === "schedules"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Schedules
          </button>
        </nav>
      </div>

      {activeTab === "history" && (
        <div>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
              No reports generated yet
            </div>
          ) : (
            <div className="bg-white border rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Report Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {history.map((item) => (
                    <tr key={item.report_id}>
                      <td className="px-6 py-4 text-sm text-gray-900 capitalize">
                        {item.report_type}
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(item.status)}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatDate(item.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        {item.status === "completed" && (
                          <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                            Download
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "schedules" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Scheduled Reports</h2>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              New Schedule
            </button>
          </div>

          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : schedules.length === 0 ? (
            <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
              No schedules configured yet
            </div>
          ) : (
            <div className="bg-white border rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frequency</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Devices</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Run</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {schedules.map((schedule) => (
                    <tr key={schedule.schedule_id}>
                      <td className="px-6 py-4 text-sm text-gray-900 capitalize">
                        {schedule.report_type}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 capitalize">
                        {schedule.frequency}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {schedule.params_template?.device_ids?.length || 0} devices
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatDate(schedule.next_run_at)}
                      </td>
                      <td className="px-6 py-4">
                        {getStatusBadge(schedule.last_status || "pending")}
                      </td>
                      <td className="px-6 py-4">
                        {schedule.is_active && (
                          <button
                            onClick={() => handleDeleteSchedule(schedule.schedule_id)}
                            className="text-red-600 hover:text-red-800 text-sm font-medium"
                          >
                            Deactivate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Schedule</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Report Type</label>
                <select
                  value={formData.report_type}
                  onChange={(e) => setFormData({ ...formData, report_type: e.target.value as "consumption" | "comparison" })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="consumption">Energy Consumption</option>
                  <option value="comparison">Comparison</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
                <select
                  value={formData.frequency}
                  onChange={(e) => setFormData({ ...formData, frequency: e.target.value as "daily" | "weekly" | "monthly" })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Group By</label>
                <select
                  value={formData.group_by}
                  onChange={(e) => setFormData({ ...formData, group_by: e.target.value as "daily" | "weekly" })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Devices</label>
                <div className="border rounded-lg max-h-40 overflow-y-auto p-2 space-y-1">
                  {devices.map((device) => (
                    <label key={device.id} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.device_ids.includes(device.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({ ...formData, device_ids: [...formData.device_ids, device.id] });
                          } else {
                            setFormData({ ...formData, device_ids: formData.device_ids.filter(id => id !== device.id) });
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm">{device.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 border text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSchedule}
                disabled={submitting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
