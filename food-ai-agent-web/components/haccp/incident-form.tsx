"use client";

import { useState } from "react";
import { useSiteStore } from "@/lib/stores/site-store";

interface IncidentFormProps {
  onSubmit: (body: {
    site_id: string;
    incident_type: string;
    severity: string;
    description: string;
  }) => void;
  isLoading: boolean;
  onClose: () => void;
}

const INCIDENT_TYPES = [
  { value: "food_safety", label: "Food Safety" },
  { value: "contamination", label: "Contamination" },
  { value: "temperature", label: "Temperature" },
  { value: "other", label: "Other" },
];

const SEVERITY_LEVELS = [
  { value: "low", label: "Low", color: "bg-gray-100 text-gray-700" },
  { value: "medium", label: "Medium", color: "bg-amber-100 text-amber-700" },
  { value: "high", label: "High", color: "bg-orange-100 text-orange-700" },
  { value: "critical", label: "Critical", color: "bg-red-100 text-red-700" },
];

export function IncidentForm({ onSubmit, isLoading, onClose }: IncidentFormProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const [type, setType] = useState("food_safety");
  const [severity, setSeverity] = useState("medium");
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteId) return;
    onSubmit({
      site_id: siteId,
      incident_type: type,
      severity,
      description,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-card p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold">Report Incident</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Incident Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              {INCIDENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium">Severity</label>
            <div className="mt-1 flex gap-2">
              {SEVERITY_LEVELS.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setSeverity(s.value)}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    severity === s.value
                      ? s.color + " ring-2 ring-primary"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
              rows={4}
              placeholder="Describe the incident in detail..."
              required
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isLoading || !description.trim()}
              className="flex-1 rounded-md bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {isLoading ? "Reporting..." : "Report Incident"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-md border py-2 text-sm font-medium hover:bg-muted/50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
