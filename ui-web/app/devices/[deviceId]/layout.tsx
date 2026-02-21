"use client";

import { useEffect, useState } from "react";
import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { getDeviceById, Device } from "@/lib/deviceApi";

interface DeviceLayoutProps {
  children: React.ReactNode;
}

type Tab = {
  name: string;
  href?: string;
  disabled?: boolean;
};

export default function DeviceLayout({ children }: DeviceLayoutProps) {
  const params = useParams();
  const pathname = usePathname();
  const deviceId = (params.deviceId as string) || "";
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!deviceId) return;

    const fetchDevice = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getDeviceById(deviceId);
        setDevice(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch device details"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchDevice();
  }, [deviceId]);

  const tabs: Tab[] = [
    { name: "Telemetry", href: `/devices/${deviceId}/telemetry` },
    { name: "Stats", href: `/devices/${deviceId}/stats` },
    { name: "Charts", href: `/devices/${deviceId}/charts` },
    { name: "Alerts", href: `/devices/${deviceId}/alerts` },
  ];

  const isActiveTab = (href?: string) => {
    if (!href) return false;
    return pathname === href;
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      {/* Header with device info */}
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-start justify-between">
              <div>
                {loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-zinc-900 dark:border-zinc-50" />
                    <span className="text-zinc-600 dark:text-zinc-400">
                      Loading device details...
                    </span>
                  </div>
                ) : error ? (
                  <div>
                    <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                      Device {deviceId}
                    </h1>
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                      Error loading device: {error}
                    </p>
                  </div>
                ) : device ? (
                  <div>
                    <div className="flex items-center space-x-3">
                      <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                        {device.name}
                      </h1>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          device.status === "active"
                            ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                            : device.status === "inactive"
                            ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                            : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                        }`}
                      >
                        {device.status}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-zinc-600 dark:text-zinc-400">
                      <span>
                        <span className="font-medium">ID:</span> {device.id}
                      </span>
                      <span>
                        <span className="font-medium">Type:</span>{" "}
                        <span className="capitalize">{device.type}</span>
                      </span>
                      {device.location && (
                        <span>
                          <span className="font-medium">Location:</span>{" "}
                          {device.location}
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                    Device {deviceId}
                  </h1>
                )}
              </div>

              <Link
                href="/devices"
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                ← Back to Devices
              </Link>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              if (tab.disabled) {
                return (
                  <span
                    key={tab.name}
                    className="whitespace-nowrap py-4 px-1 border-b-2 border-transparent text-zinc-400 cursor-not-allowed text-sm font-medium"
                  >
                    {tab.name}
                    <span className="ml-2 text-xs">(soon)</span>
                  </span>
                );
              }

              const isActive = isActiveTab(tab.href);

              return (
                <Link
                  key={tab.name}
                  href={tab.href!}
                  className={`
                    whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                    ${
                      isActive
                        ? "border-blue-500 text-blue-600 dark:text-blue-400"
                        : "border-transparent text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-600"
                    }
                  `}
                  aria-current={isActive ? "page" : undefined}
                >
                  {tab.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Page Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
