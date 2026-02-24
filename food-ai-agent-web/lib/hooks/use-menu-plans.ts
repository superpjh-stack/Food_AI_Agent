"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import type { MenuPlan, PaginatedResponse } from "@/types";

interface ListParams {
  page?: number;
  per_page?: number;
  status?: string;
}

export function useMenuPlans(params: ListParams = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { page = 1, per_page = 20, status } = params;

  return useQuery({
    queryKey: ["menu-plans", siteId, page, per_page, status],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (status) qs.set("status", status);
      if (siteId) qs.set("site_id", siteId);
      const res = await http<PaginatedResponse<MenuPlan>>(`/menu-plans?${qs}`);
      return res as unknown as PaginatedResponse<MenuPlan>;
    },
    enabled: !!siteId,
  });
}

export function useMenuPlan(planId: string | undefined) {
  return useQuery({
    queryKey: ["menu-plan", planId],
    queryFn: () => http<MenuPlan>(`/menu-plans/${planId}`),
    enabled: !!planId,
  });
}

export function useGenerateMenuPlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: {
      site_id: string;
      period_start: string;
      period_end: string;
      meal_types: string[];
      target_headcount: number;
      budget_per_meal?: number;
      preferences?: string;
    }) =>
      http<MenuPlan>("/menu-plans/generate", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["menu-plans"] });
    },
  });
}

export function useUpdateMenuPlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: Partial<MenuPlan> }) =>
      http<MenuPlan>(`/menu-plans/${planId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["menu-plan", variables.planId] });
      queryClient.invalidateQueries({ queryKey: ["menu-plans"] });
    },
  });
}

export function useValidateMenuPlan() {
  return useMutation({
    mutationFn: (planId: string) =>
      http<{ overall_status: string; daily_results: Record<string, unknown> }>(
        `/menu-plans/${planId}/validate`,
        { method: "POST" }
      ),
  });
}

export function useConfirmMenuPlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (planId: string) =>
      http<MenuPlan>(`/menu-plans/${planId}/confirm`, { method: "POST" }),
    onSuccess: (_data, planId) => {
      queryClient.invalidateQueries({ queryKey: ["menu-plan", planId] });
      queryClient.invalidateQueries({ queryKey: ["menu-plans"] });
    },
  });
}
