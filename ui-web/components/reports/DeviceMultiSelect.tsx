"use client";

import { useState, useEffect } from "react";
import { getDevices, Device } from "@/lib/deviceApi";

interface DeviceMultiSelectProps {
  tenantId: string;
  onChange: (deviceIds: string[]) => void;
  disabled?: boolean;
}

export function DeviceMultiSelect({ tenantId, onChange, disabled }: DeviceMultiSelectProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectAll, setSelectAll] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function fetchDevices() {
      try {
        const data = await getDevices();
        setDevices(data);
      } catch (error) {
        console.error("Failed to fetch devices:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchDevices();
  }, [tenantId]);

  const handleSelectAll = (checked: boolean) => {
    setSelectAll(checked);
    if (checked) {
      onChange(["all"]);
    } else {
      setSelected(new Set());
      onChange([]);
    }
  };

  const handleDeviceToggle = (deviceId: string, checked: boolean) => {
    const newSelected = new Set(selected);
    if (checked) {
      newSelected.add(deviceId);
    } else {
      newSelected.delete(deviceId);
    }
    setSelected(newSelected);
    onChange(Array.from(newSelected));
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-500">Loading devices...</div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 pb-3 border-b">
        <input
          type="checkbox"
          id="selectAllDevices"
          checked={selectAll}
          onChange={(e) => handleSelectAll(e.target.checked)}
          disabled={disabled}
          className="w-4 h-4 rounded border-gray-300"
        />
        <label htmlFor="selectAllDevices" className="text-sm font-medium text-gray-700">
          All Devices
        </label>
        <span className="ml-auto text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
          {devices.length} devices
        </span>
      </div>

      <div className="max-h-60 overflow-y-auto space-y-1">
        {devices.map((device) => (
          <label
            key={device.id}
            className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.has(device.id)}
              onChange={(e) => handleDeviceToggle(device.id, e.target.checked)}
              disabled={disabled || selectAll}
              className="w-4 h-4 rounded border-gray-300"
            />
            <span className="text-sm text-gray-700">{device.name}</span>
            <span className="text-xs text-gray-400 ml-auto">{device.type}</span>
          </label>
        ))}
      </div>

      {devices.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-4">No devices found</p>
      )}
    </div>
  );
}
