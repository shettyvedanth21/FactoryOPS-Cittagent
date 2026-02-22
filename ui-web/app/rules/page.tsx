"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRules, createRule, updateRuleStatus, deleteRule, Rule, RuleStatus } from "@/lib/ruleApi";
import { getDevices, Device } from "@/lib/deviceApi";
import { getAllDevicesProperties, getCommonProperties, getDeviceProperties } from "@/lib/dataApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select, Checkbox } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/ui/badge";

const CONDITION_OPTIONS = [
  { value: ">", label: "Greater than (> )" },
  { value: ">=", label: "Greater than or equal (>=)" },
  { value: "<", label: "Less than (<)" },
  { value: "<=", label: "Less than or equal (<=)" },
  { value: "==", label: "Equal to (==)" },
  { value: "!=", label: "Not equal to (!=)" },
];

const SCOPE_OPTIONS = [
  { value: "all_devices", label: "All Devices" },
  { value: "selected_devices", label: "Selected Devices" },
];

const METRIC_LABELS: Record<string, string> = {
  power: "Power", voltage: "Voltage", current: "Current", temperature: "Temperature",
  pressure: "Pressure", humidity: "Humidity", vibration: "Vibration", frequency: "Frequency",
  power_factor: "Power Factor", speed: "Speed", torque: "Torque", oil_pressure: "Oil Pressure",
};

function formatPropertyLabel(property: string): string {
  return METRIC_LABELS[property] || property.charAt(0).toUpperCase() + property.slice(1).replace(/_/g, ' ');
}

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  
  const [allDeviceProperties, setAllDeviceProperties] = useState<Record<string, string[]>>({});
  const [availableProperties, setAvailableProperties] = useState<{value: string, label: string}[]>([]);
  const [propertiesLoading, setPropertiesLoading] = useState(true);
  
  const [formData, setFormData] = useState<{
    ruleName: string;
    scope: "all_devices" | "selected_devices";
    selectedDevices: string[];
    property: string;
    condition: string;
    threshold: string;
    enabled: boolean;
    email: boolean;
    whatsapp: boolean;
    telegram: boolean;
  }>({
    ruleName: "",
    scope: "all_devices",
    selectedDevices: [],
    property: "",
    condition: ">",
    threshold: "",
    enabled: true,
    email: false,
    whatsapp: false,
    telegram: false,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rulesResponse, devicesData, propsData] = await Promise.all([
        listRules(),
        getDevices(),
        getAllDevicesProperties(),
      ]);
      setRules(rulesResponse.data);
      setDevices(devicesData);
      setAllDeviceProperties(propsData.devices);
      
      const allProps = propsData.all_properties;
      setAvailableProperties(allProps.map(p => ({
        value: p,
        label: formatPropertyLabel(p)
      })));
      
      if (allProps.length > 0 && !formData.property) {
        setFormData(prev => ({ ...prev, property: allProps[0] }));
      }
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
      setPropertiesLoading(false);
    }
  };

  useEffect(() => {
    async function updateAvailableProperties() {
      if (formData.scope === "all_devices") {
        const activeDevices = devices.filter(d => d.status === "active").map(d => d.id);
        if (activeDevices.length > 0) {
          try {
            const common = await getCommonProperties(activeDevices);
            const props = common.properties.map(p => ({
              value: p,
              label: formatPropertyLabel(p)
            }));
            setAvailableProperties(props);
            if (!props.find(p => p.value === formData.property)) {
              setFormData(prev => ({ 
                ...prev, 
                property: props.length > 0 ? props[0].value : "" 
              }));
            }
          } catch (err) {
            console.error("Failed to get common properties:", err);
          }
        }
      } else if (formData.selectedDevices.length === 1) {
        try {
          const deviceId = formData.selectedDevices[0];
          const props = await getDeviceProperties(deviceId);
          const formattedProps = props.map(p => ({
            value: p,
            label: formatPropertyLabel(p)
          }));
          setAvailableProperties(formattedProps);
          if (!formattedProps.find(p => p.value === formData.property)) {
            setFormData(prev => ({ 
              ...prev, 
              property: formattedProps.length > 0 ? formattedProps[0].value : "" 
            }));
          }
        } catch (err) {
          console.error("Failed to get device properties:", err);
          setAvailableProperties([]);
          setFormData(prev => ({ ...prev, property: "" }));
        }
      } else if (formData.selectedDevices.length > 1) {
        try {
          const common = await getCommonProperties(formData.selectedDevices);
          const props = common.properties.map(p => ({
            value: p,
            label: formatPropertyLabel(p)
          }));
          setAvailableProperties(props);
          if (!props.find(p => p.value === formData.property)) {
            setFormData(prev => ({ 
              ...prev, 
              property: props.length > 0 ? props[0].value : "" 
            }));
          }
        } catch (err) {
          console.error("Failed to get common properties:", err);
        }
      } else {
        setAvailableProperties([]);
        setFormData(prev => ({ ...prev, property: "" }));
      }
    }
    
    updateAvailableProperties();
  }, [formData.scope, formData.selectedDevices, devices]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.property) {
      alert("Please select a property");
      return;
    }
    
    const channels: string[] = [];
    if (formData.email) channels.push("email");
    if (formData.whatsapp) channels.push("whatsapp");
    if (formData.telegram) channels.push("telegram");
    
    try {
      await createRule({
        ruleName: formData.ruleName,
        property: formData.property,
        condition: formData.condition,
        threshold: parseFloat(formData.threshold),
        scope: formData.scope,
        deviceIds: formData.scope === "selected_devices" ? formData.selectedDevices : [],
        notificationChannels: channels,
        cooldownMinutes: 5,
      });
      
      setShowForm(false);
      resetForm();
      loadData();
    } catch (err) {
      console.error("Failed to create rule:", err);
    }
  };

  const handleToggleStatus = async (ruleId: string, currentStatus: RuleStatus) => {
    const newStatus = currentStatus === "active" ? "paused" : "active";
    try {
      await updateRuleStatus(ruleId, newStatus);
      loadData();
    } catch (err) {
      console.error("Failed to update rule status:", err);
    }
  };

  const handleDelete = async (ruleId: string) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    
    try {
      await deleteRule(ruleId);
      loadData();
    } catch (err) {
      console.error("Failed to delete rule:", err);
    }
  };

  const resetForm = () => {
    setFormData({
      ruleName: "",
      scope: "all_devices",
      selectedDevices: [],
      property: availableProperties.length > 0 ? availableProperties[0].value : "",
      condition: ">",
      threshold: "",
      enabled: true,
      email: false,
      whatsapp: false,
      telegram: false,
    });
  };

  const getConditionLabel = (condition: string) => {
    const found = CONDITION_OPTIONS.find((o) => o.value === condition);
    return found ? found.label : condition;
  };

  const getDeviceNames = (deviceIds: string[]) => {
    if (deviceIds.length === 0) return "All devices";
    return deviceIds
      .map((id) => devices.find((d) => d.id === id)?.name || id)
      .join(", ");
  };

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Rules</h1>
            <p className="text-slate-500 mt-1">
              Manage monitoring rules across all machines
            </p>
          </div>
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Add Rule"}
          </Button>
        </div>

        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle>Create New Rule</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Rule Name"
                    value={formData.ruleName}
                    onChange={(e) => setFormData({ ...formData, ruleName: e.target.value })}
                    required
                  />
                  
                  <Select
                    label="Scope"
                    value={formData.scope}
                    onChange={(e) => setFormData({ ...formData, scope: e.target.value as any, selectedDevices: [] })}
                    options={SCOPE_OPTIONS}
                  />
                  
                  {formData.scope === "selected_devices" && (
                    <div className="md:col-span-2">
                      <p className="text-sm font-medium text-slate-700 mb-2">Select Devices</p>
                      <div className="flex flex-wrap gap-3">
                        {devices.map((device) => (
                          <label
                            key={device.id}
                            className="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100"
                          >
                            <input
                              type="checkbox"
                              checked={formData.selectedDevices.includes(device.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setFormData({
                                    ...formData,
                                    selectedDevices: [...formData.selectedDevices, device.id],
                                  });
                                } else {
                                  setFormData({
                                    ...formData,
                                    selectedDevices: formData.selectedDevices.filter(
                                      (id) => id !== device.id
                                    ),
                                  });
                                }
                              }}
                              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm text-slate-700">{device.name}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {propertiesLoading ? (
                    <div className="md:col-span-2">
                      <p className="text-sm font-medium text-slate-700 mb-1">Property</p>
                      <div className="text-sm text-slate-500 py-2">Loading properties...</div>
                    </div>
                  ) : availableProperties.length === 0 ? (
                    <div className="md:col-span-2">
                      <p className="text-sm font-medium text-slate-700 mb-1">Property</p>
                      <div className="text-sm text-red-500 py-2">
                        {formData.scope === "selected_devices" && formData.selectedDevices.length === 0
                          ? "Select devices to see available properties"
                          : "No common properties available. Devices may have different telemetry fields."}
                      </div>
                    </div>
                  ) : (
                    <Select
                      label="Property"
                      value={formData.property}
                      onChange={(e) => setFormData({ ...formData, property: e.target.value })}
                      options={availableProperties}
                    />
                  )}
                  
                  <Select
                    label="Condition"
                    value={formData.condition}
                    onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
                    options={CONDITION_OPTIONS}
                  />
                  
                  <Input
                    label="Threshold Value"
                    type="number"
                    step="0.01"
                    value={formData.threshold}
                    onChange={(e) => setFormData({ ...formData, threshold: e.target.value })}
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700">Notification Channels</p>
                  <div className="flex gap-6">
                    <Checkbox
                      label="Email"
                      checked={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.checked })}
                    />
                    <Checkbox
                      label="WhatsApp"
                      checked={formData.whatsapp}
                      onChange={(e) => setFormData({ ...formData, whatsapp: e.target.checked })}
                    />
                    <Checkbox
                      label="Telegram"
                      checked={formData.telegram}
                      onChange={(e) => setFormData({ ...formData, telegram: e.target.checked })}
                    />
                  </div>
                </div>
                
                <div className="flex gap-3 pt-4">
                  <Button type="submit" disabled={propertiesLoading || availableProperties.length === 0}>
                    Create Rule
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowForm(false);
                      resetForm();
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>All Rules ({rules.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-sm text-slate-500">Loading rules...</p>
                </div>
              ) : rules.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium text-slate-900 mb-2">No rules found</h3>
                  <p className="text-sm mb-4">Create your first rule to start monitoring</p>
                  <Button onClick={() => setShowForm(true)}>Create Rule</Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rule Name</TableHead>
                      <TableHead>Property</TableHead>
                      <TableHead>Condition</TableHead>
                      <TableHead>Devices</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rules.map((rule) => (
                      <TableRow key={rule.ruleId}>
                        <TableCell className="font-medium">{rule.ruleName}</TableCell>
                        <TableCell className="capitalize">{formatPropertyLabel(rule.property)}</TableCell>
                        <TableCell>
                          {getConditionLabel(rule.condition)} {rule.threshold}
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-slate-500">
                            {getDeviceNames(rule.deviceIds)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={rule.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleToggleStatus(rule.ruleId, rule.status)}
                              className={`text-sm px-3 py-1 rounded transition-colors ${
                                rule.status === "active"
                                  ? "text-amber-600 hover:bg-amber-50"
                                  : "text-green-600 hover:bg-green-50"
                              }`}
                            >
                              {rule.status === "active" ? "Pause" : "Enable"}
                            </button>
                            <Link
                              href={`/machines/${rule.deviceIds[0] || devices[0]?.id || 'D1'}`}
                              className="text-sm text-blue-600 hover:text-blue-800 px-3 py-1 hover:bg-blue-50 rounded"
                            >
                              View
                            </Link>
                            <button
                              onClick={() => handleDelete(rule.ruleId)}
                              className="text-sm text-red-600 hover:text-red-800 px-3 py-1 hover:bg-red-50 rounded"
                            >
                              Delete
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
