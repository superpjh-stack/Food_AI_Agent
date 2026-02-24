"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import type { HaccpChecklist, HaccpRecord, HaccpIncident, PaginatedResponse } from "@/types";

// ── Checklists ──

export function useHACCPChecklists(params: { date?: string; status?: string } = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["haccp-checklists", siteId, params.date, params.status],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      if (params.date) qs.set("date", params.date);
      if (params.status) qs.set("status", params.status);
      return http<PaginatedResponse<HaccpChecklist>>(`/haccp/checklists?${qs}`) as unknown as PaginatedResponse<HaccpChecklist>;
    },
    enabled: !!siteId,
  });
}

export function useHACCPChecklist(checklistId: string | undefined) {
  return useQuery({
    queryKey: ["haccp-checklist", checklistId],
    queryFn: () => http<HaccpChecklist & { records: HaccpRecord[] }>(`/haccp/checklists/${checklistId}`),
    enabled: !!checklistId,
  });
}

export function useGenerateChecklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      date: string;
      checklist_type: string;
      meal_type?: string;
    }) => http<HaccpChecklist>("/haccp/checklists/generate", {
      method: "POST",
      body: JSON.stringify(params),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["haccp-checklists"] });
    },
  });
}

export function useSubmitChecklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (checklistId: string) =>
      http<HaccpChecklist>(`/haccp/checklists/${checklistId}/submit`, { method: "POST" }),
    onSuccess: (_data, checklistId) => {
      queryClient.invalidateQueries({ queryKey: ["haccp-checklist", checklistId] });
      queryClient.invalidateQueries({ queryKey: ["haccp-checklists"] });
    },
  });
}

// ── CCP Records ──

export function useCCPRecords(checklistId: string | undefined) {
  return useQuery({
    queryKey: ["haccp-records", checklistId],
    queryFn: async () => {
      const qs = checklistId ? `?checklist_id=${checklistId}` : "";
      return http<HaccpRecord[]>(`/haccp/records${qs}`);
    },
    enabled: !!checklistId,
  });
}

export function useCreateCCPRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      checklist_id: string;
      ccp_point: string;
      category?: string;
      target_value?: string;
      actual_value?: string;
      is_compliant?: boolean;
      corrective_action?: string;
    }) => http<HaccpRecord>("/haccp/records", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["haccp-records", variables.checklist_id] });
      queryClient.invalidateQueries({ queryKey: ["haccp-checklist", variables.checklist_id] });
    },
  });
}

// ── Incidents ──

export function useIncidents(params: { status?: string } = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["haccp-incidents", siteId, params.status],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      if (params.status) qs.set("status", params.status);
      return http<PaginatedResponse<HaccpIncident>>(`/haccp/incidents?${qs}`) as unknown as PaginatedResponse<HaccpIncident>;
    },
    enabled: !!siteId,
  });
}

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      site_id: string;
      incident_type: string;
      severity: string;
      description: string;
    }) => http<HaccpIncident>("/haccp/incidents", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["haccp-incidents"] });
    },
  });
}

export function useUpdateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ incidentId, data }: { incidentId: string; data: Record<string, unknown> }) =>
      http<HaccpIncident>(`/haccp/incidents/${incidentId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["haccp-incidents"] });
    },
  });
}

// ── Audit Report ──

export function useAuditReport() {
  return useMutation({
    mutationFn: (body: {
      site_id: string;
      start_date: string;
      end_date: string;
    }) => http<Record<string, unknown>>("/haccp/reports/audit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  });
}

// ── Completion Status ──

export function useCompletionStatus(date?: string) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["haccp-completion", siteId, date],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      if (date) qs.set("date", date);
      return http<{
        date: string;
        total: number;
        completed: number;
        in_progress: number;
        pending: number;
        overdue: number;
        completion_rate: number;
      }>(`/haccp/completion-status?${qs}`);
    },
    enabled: !!siteId,
  });
}
