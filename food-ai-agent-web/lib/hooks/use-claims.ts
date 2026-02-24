"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";

export interface Claim {
  id: string;
  site_id: string;
  incident_date: string;
  category: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  menu_plan_id: string | null;
  recipe_id: string | null;
  lot_number: string | null;
  reporter_name: string | null;
  reporter_role: string | null;
  haccp_incident_id: string | null;
  ai_hypotheses: Array<Record<string, unknown>>;
  root_cause: string | null;
  is_recurring: boolean;
  recurrence_count: number;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimAction {
  id: string;
  claim_id: string;
  action_type: string;
  description: string;
  assignee_id: string | null;
  assignee_role: string | null;
  due_date: string | null;
  status: string;
  result_notes: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ClaimsFilters {
  status?: string;
  category?: string;
  severity?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  perPage?: number;
}

export function useClaimsList(filters: ClaimsFilters = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { status, category, severity, dateFrom, dateTo, page = 1, perPage = 20 } = filters;

  return useQuery({
    queryKey: ["claims", siteId, status, category, severity, dateFrom, dateTo, page],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(perPage) });
      if (siteId) qs.set("site_id", siteId);
      if (status) qs.set("status", status);
      if (category) qs.set("category", category);
      if (severity) qs.set("severity", severity);
      if (dateFrom) qs.set("date_from", dateFrom);
      if (dateTo) qs.set("date_to", dateTo);
      return http<{ data: Claim[]; meta: { total: number; page: number; per_page: number } }>(
        `/claims?${qs}`
      );
    },
    enabled: !!siteId,
  });
}

export function useClaim(claimId: string | undefined) {
  return useQuery({
    queryKey: ["claim", claimId],
    queryFn: () => http<Claim>(`/claims/${claimId}`),
    enabled: !!claimId,
  });
}

export function useCreateClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      incident_date: string;
      category: string;
      severity?: string;
      title: string;
      description: string;
      menu_plan_id?: string;
      recipe_id?: string;
      lot_number?: string;
      reporter_name?: string;
      reporter_role?: string;
    }) =>
      http<{
        claim_id: string;
        status: string;
        haccp_incident_created: boolean;
        is_recurring: boolean;
      }>("/claims", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["claims"] });
    },
  });
}

export function useUpdateClaimStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      claimId,
      status,
      rootCause,
    }: {
      claimId: string;
      status: string;
      rootCause?: string;
    }) =>
      http<Claim>(`/claims/${claimId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status, root_cause: rootCause }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["claim", variables.claimId] });
      queryClient.invalidateQueries({ queryKey: ["claims"] });
    },
  });
}

export function useAddClaimAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      claimId,
      ...params
    }: {
      claimId: string;
      action_type: string;
      description: string;
      assignee_role: string;
      assignee_id?: string;
      due_date?: string;
    }) =>
      http<unknown>(`/claims/${claimId}/actions`, {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["claim", variables.claimId] });
      queryClient.invalidateQueries({ queryKey: ["claim-actions", variables.claimId] });
    },
  });
}

export function useClaimActions(claimId: string | undefined) {
  return useQuery({
    queryKey: ["claim-actions", claimId],
    queryFn: () => http<ClaimAction[]>(`/claims/${claimId}/actions`),
    enabled: !!claimId,
  });
}

export function useQualityReport(siteId: string | undefined, month: number, year: number) {
  return useQuery({
    queryKey: ["quality-report", siteId, month, year],
    queryFn: async () => {
      const qs = new URLSearchParams({
        site_id: siteId!,
        month: String(month),
        year: String(year),
      });
      return http<{
        site_id: string;
        year: number;
        month: number;
        total_claims: number;
        by_category: Record<string, number>;
        by_severity: Record<string, number>;
        by_status: Record<string, number>;
        recurring_claims: number;
        avg_resolution_days: number | null;
        open_critical: number;
      }>(`/claims/reports/quality?${qs}`);
    },
    enabled: !!siteId && !!month && !!year,
  });
}

export function useAnalyzeClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, useRag = true }: { claimId: string; useRag?: boolean }) =>
      http<{
        hypotheses: Array<Record<string, unknown>>;
        related_data: Record<string, unknown>;
        rag_references_count: number;
      }>(`/claims/${claimId}/analyze?use_rag=${useRag}`, { method: "POST" }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["claim", variables.claimId] });
    },
  });
}
