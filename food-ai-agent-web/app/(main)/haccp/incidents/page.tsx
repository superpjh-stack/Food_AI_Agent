"use client";

import { useState } from "react";
import { useIncidents, useCreateIncident, useUpdateIncident } from "@/lib/hooks/use-haccp";
import { IncidentForm } from "@/components/haccp/incident-form";
import { IncidentResponseSteps } from "@/components/haccp/incident-response-steps";
import { cn } from "@/lib/utils/cn";

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  open: { label: "Open", color: "bg-red-100 text-red-700" },
  in_progress: { label: "In Progress", color: "bg-blue-100 text-blue-700" },
  resolved: { label: "Resolved", color: "bg-green-100 text-green-700" },
  closed: { label: "Closed", color: "bg-gray-100 text-gray-700" },
};

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-gray-100 text-gray-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

interface Incident {
  id: string;
  incident_type: string;
  severity: string;
  description: string;
  steps_taken: { step: number; action: string; done: boolean }[];
  status: string;
  created_at: string;
}

export default function IncidentsPage() {
  const [showForm, setShowForm] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data, isLoading } = useIncidents();
  const createMutation = useCreateIncident();
  const updateMutation = useUpdateIncident();

  const incidents = ((data as unknown as { data: Incident[] })?.data ?? []) as Incident[];
  const selected = incidents.find((i) => i.id === selectedId);

  const handleCreate = async (body: {
    site_id: string;
    incident_type: string;
    severity: string;
    description: string;
  }) => {
    const result = await createMutation.mutateAsync(body);
    setShowForm(false);
    if (result?.id) setSelectedId(result.id as unknown as string);
  };

  const handleToggleStep = async (incident: Incident, stepIdx: number) => {
    const updatedSteps = incident.steps_taken.map((s, i) =>
      i === stepIdx ? { ...s, done: !s.done } : s
    );
    await updateMutation.mutateAsync({
      incidentId: incident.id,
      data: { steps_taken: updatedSteps },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Incidents</h1>
          <p className="text-sm text-muted-foreground">Food safety incidents and response tracking</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          + Report Incident
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* List */}
        <div className="space-y-2">
          {isLoading ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground">Loading...</div>
          ) : incidents.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground">
              No incidents reported.
            </div>
          ) : (
            incidents.map((inc) => {
              const status = STATUS_STYLES[inc.status] ?? STATUS_STYLES.open;
              return (
                <button
                  key={inc.id}
                  onClick={() => setSelectedId(inc.id)}
                  className={cn(
                    "w-full rounded-lg border p-3 text-left transition-colors",
                    selectedId === inc.id ? "ring-2 ring-primary" : "hover:bg-muted/30",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", SEVERITY_STYLES[inc.severity])}>
                      {inc.severity}
                    </span>
                    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", status.color)}>
                      {status.label}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium">{inc.incident_type}</p>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{inc.description}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(inc.created_at).toLocaleDateString("ko-KR")}
                  </p>
                </button>
              );
            })
          )}
        </div>

        {/* Detail */}
        <div>
          {selected ? (
            <div className="space-y-4">
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold">{selected.incident_type}</h3>
                <p className="mt-2 text-sm">{selected.description}</p>
                <div className="mt-3 flex gap-2">
                  {selected.status === "open" && (
                    <button
                      onClick={() => updateMutation.mutate({ incidentId: selected.id, data: { status: "in_progress" } })}
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Start Investigation
                    </button>
                  )}
                  {selected.status === "in_progress" && (
                    <button
                      onClick={() => updateMutation.mutate({ incidentId: selected.id, data: { status: "resolved" } })}
                      className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
                    >
                      Mark Resolved
                    </button>
                  )}
                </div>
              </div>

              <IncidentResponseSteps
                steps={selected.steps_taken}
                severity={selected.severity}
                onToggle={(idx) => handleToggleStep(selected, idx)}
              />
            </div>
          ) : (
            <div className="flex h-60 items-center justify-center rounded-lg border text-muted-foreground">
              Select an incident to view details
            </div>
          )}
        </div>
      </div>

      {showForm && (
        <IncidentForm
          onSubmit={handleCreate}
          isLoading={createMutation.isPending}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
