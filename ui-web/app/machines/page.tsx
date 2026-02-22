"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getDevices, Device } from "@/lib/deviceApi";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatIST, getRelativeTime } from "@/lib/utils";

export default function MachinesPage() {
  const [machines, setMachines] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchMachines = useCallback(async () => {
    setError(null);
    try {
      const data = await getDevices();
      setMachines(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch machines");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMachines();
    
    // Auto-refresh every 10 seconds to keep relative time accurate
    const interval = setInterval(fetchMachines, 10000);
    
    return () => clearInterval(interval);
  }, [fetchMachines]);

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-slate-600">Loading machines...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 font-semibold mb-2">Error loading machines</h2>
          <p className="text-red-600">{error}</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Machines</h1>
            <p className="text-slate-500 mt-1">
              Monitor and manage your industrial equipment
            </p>
          </div>
          <div className="text-sm text-slate-500">
            {machines.length} machine{machines.length !== 1 ? 's' : ''}
          </div>
        </div>

        {machines.length === 0 ? (
          <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-slate-900 mb-2">No machines found</h3>
            <p className="text-slate-500 mb-4">
              Get started by adding your first machine to the platform.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {machines.map((machine) => (
              <Link key={machine.id} href={`/machines/${machine.id}`}>
                <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h2 className="text-lg font-semibold text-slate-900">
                          {machine.name}
                        </h2>
                        <p className="text-sm text-slate-500 font-mono mt-0.5">
                          {machine.id}
                        </p>
                      </div>
                      <StatusBadge status={machine.runtime_status} />
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500">Type</span>
                        <span className="text-slate-900 capitalize">
                          {machine.type}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500">Location</span>
                        <span className="text-slate-900">
                          {machine.location || "—"}
                        </span>
                      </div>
                      {machine.last_seen_timestamp ? (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-500">Last Seen</span>
                          <span className="text-slate-900 text-xs">
                            {formatIST(machine.last_seen_timestamp)}
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-500">Last Seen</span>
                          <span className="text-slate-900 text-xs">No data received</span>
                        </div>
                      )}
                    </div>
                    <div className="mt-4 pt-4 border-t border-slate-100">
                      <span className="text-sm text-blue-600 font-medium flex items-center gap-1">
                        View Dashboard
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
