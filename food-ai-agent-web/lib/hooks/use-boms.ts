"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import type { Bom, PaginatedResponse } from "@/types";

interface ListParams {
  page?: number;
  per_page?: number;
  status?: string;
  period_start?: string;
  period_end?: string;
}

export function useBoms(params: ListParams = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { page = 1, per_page = 20, status, period_start, period_end } = params;

  return useQuery({
    queryKey: ["boms", siteId, page, per_page, status, period_start, period_end],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (siteId) qs.set("site_id", siteId);
      if (status) qs.set("status", status);
      if (period_start) qs.set("period_start", period_start);
      if (period_end) qs.set("period_end", period_end);
      const res = await http<PaginatedResponse<Bom>>(`/boms?${qs}`);
      return res as unknown as PaginatedResponse<Bom>;
    },
    enabled: !!siteId,
  });
}

export function useBom(bomId: string | undefined) {
  return useQuery({
    queryKey: ["bom", bomId],
    queryFn: () => http<Bom>(`/boms/${bomId}`),
    enabled: !!bomId,
  });
}

export function useBomCostAnalysis(bomId: string | undefined) {
  return useQuery({
    queryKey: ["bom-cost-analysis", bomId],
    queryFn: () => http<unknown>(`/boms/${bomId}/cost-analysis`),
    enabled: !!bomId,
  });
}

export function useGenerateBom() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: {
      menu_plan_id: string;
      headcount: number;
      apply_inventory?: boolean;
    }) =>
      http<Bom>("/boms/generate", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boms"] });
    },
  });
}

export function useUpdateBom() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ bomId, data }: { bomId: string; data: { headcount?: number; items?: unknown[] } }) =>
      http<Bom>(`/boms/${bomId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["bom", variables.bomId] });
      queryClient.invalidateQueries({ queryKey: ["boms"] });
    },
  });
}

export function useApplyInventoryToBom() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (bomId: string) =>
      http<unknown>(`/boms/${bomId}/apply-inventory`, { method: "POST" }),
    onSuccess: (_data, bomId) => {
      queryClient.invalidateQueries({ queryKey: ["bom", bomId] });
    },
  });
}
