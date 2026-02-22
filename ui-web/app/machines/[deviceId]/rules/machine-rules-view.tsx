"use client";

import { useEffect, useState } from "react";
import { listRules, createRule, updateRuleStatus, deleteRule, Rule, RuleStatus } from "@/lib/ruleApi";
import { getDeviceFields } from "@/lib/dataApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select, Checkbox } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/ui/badge";

interface MachineRulesViewProps {
  deviceId: string;
}

const CONDITION_OPTIONS = [
  { value: ">", label: "Greater than (> )" },
  { value: ">=", label: "Greater than or equal (>=)" },
  { value: "<", label: "Less than (<)" },
  { value: "<=", label: "Less than or equal (<=)" },
  { value: "==", label: "Equal to (==)" },
  { value: "!=", label: "Not equal to (!=)" },
];

const METRIC_LABELS: Record<string, string> = {
  power: "Power", voltage: "Voltage", current: "Current", temperature: "Temperature",
  pressure: "Pressure", humidity: "Humidity", vibration: "Vibration", frequency: "Frequency",
  power_factor: "Power Factor", speed: "Speed", torque: "Torque", oil_pressure: "Oil Pressure",
};

export function MachineRulesView({ deviceId }: MachineRulesViewProps) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [availableProperties, setAvailableProperties] = useState<{value: string, label: string}[]>([]);
  const [propertiesLoading, setPropertiesLoading] = useState(true);
  
  const [formData, setFormData] = useState({
    ruleName: "",
    property: "",
    condition: ">",
    threshold: "",
    enabled: true,
    email: false,
    whatsapp: false,
    telegram: false,
  });

  // Fetch available properties from device telemetry
  useEffect(() => {
    async function fetchProperties() {
      try {
        const fields = await getDeviceFields(deviceId);
        const properties = fields.map(field => ({
          value: field,
          label: METRIC_LABELS[field] || field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ')
        }));
        setAvailableProperties(properties);
        if (fields.length > 0 && !formData.property) {
          setFormData(prev => ({ ...prev, property: fields[0] }));
        }
      } catch (err) {
        console.error("Failed to fetch device fields:", err);
        setAvailableProperties([]);
      } finally {
        setPropertiesLoading(false);
      }
    }
    
    fetchProperties();
  }, [deviceId]);

  // Update property when available properties change
  useEffect(() => {
    if (availableProperties.length > 0 && !availableProperties.find(p => p.value === formData.property)) {
      setFormData(prev => ({ ...prev, property: availableProperties[0].value }));
    }
  }, [availableProperties, formData.property]);

  useEffect(() => {
    fetchRules();
  }, [deviceId]);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await listRules({ deviceId });
      setRules(response.data);
    } catch (err) {
      console.error("Failed to fetch rules:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
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
        scope: "selected_devices",
        deviceIds: [deviceId],
        notificationChannels: channels,
        cooldownMinutes: 5,
      });
      
      setShowForm(false);
      resetForm();
      fetchRules();
    } catch (err) {
      console.error("Failed to create rule:", err);
    }
  };

  const handleToggleStatus = async (ruleId: string, currentStatus: RuleStatus) => {
    const newStatus = currentStatus === "active" ? "paused" : "active";
    try {
      await updateRuleStatus(ruleId, newStatus);
      fetchRules();
    } catch (err) {
      console.error("Failed to update rule status:", err);
    }
  };

  const handleDelete = async (ruleId: string) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    
    try {
      await deleteRule(ruleId);
      fetchRules();
    } catch (err) {
      console.error("Failed to delete rule:", err);
    }
  };

  const resetForm = () => {
    setFormData({
      ruleName: "",
      property: "power",
      condition: ">",
      threshold: "",
      enabled: true,
      email: false,
      whatsapp: false,
      telegram: false,
    });
    setEditingRule(null);
  };

  const getConditionLabel = (condition: string) => {
    const found = CONDITION_OPTIONS.find((o) => o.value === condition);
    return found ? found.label : condition;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Machine Rules</h2>
          <p className="text-sm text-slate-500">Configure monitoring rules for this machine</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "Add Rule"}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{editingRule ? "Edit Rule" : "Create New Rule"}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Rule Name"
                  value={formData.ruleName}
                  onChange={(e) => setFormData({ ...formData, ruleName: e.target.value })}
                  required
                />
                
                {propertiesLoading ? (
                  <div className="text-sm text-slate-500 py-2">Loading properties...</div>
                ) : availableProperties.length === 0 ? (
                  <div className="text-sm text-red-500 py-2">No numeric properties found</div>
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
                <Button type="submit">
                  {editingRule ? "Update Rule" : "Create Rule"}
                </Button>
                <Button type="button" variant="outline" onClick={() => { setShowForm(false); resetForm(); }}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Active Rules</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-sm text-slate-500">Loading rules...</p>
            </div>
          ) : rules.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <p>No rules configured for this machine</p>
              <p className="text-sm mt-1">Add a rule to start monitoring</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule Name</TableHead>
                  <TableHead>Property</TableHead>
                  <TableHead>Condition</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.ruleId}>
                    <TableCell className="font-medium">{rule.ruleName}</TableCell>
                    <TableCell className="capitalize">{rule.property}</TableCell>
                    <TableCell>
                      {getConditionLabel(rule.condition)} {rule.threshold}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={rule.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleToggleStatus(rule.ruleId, rule.status)}
                          className={`text-sm px-3 py-1 rounded ${
                            rule.status === "active"
                              ? "text-amber-600 hover:bg-amber-50"
                              : "text-green-600 hover:bg-green-50"
                          }`}
                        >
                          {rule.status === "active" ? "Pause" : "Enable"}
                        </button>
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
  );
}
