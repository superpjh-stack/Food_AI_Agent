"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";

export interface CostAnalysis {
  id: string;
  site_id: string;
  menu_plan_id: string | null;
  analysis_type: string;
  target_cost: number | null;
  estimated_cost: number | null;
  actual_cost: number | null;
  headcount: number | null;
  variance_pct: number | null;
  alert_triggered: string | null;
  cost_breakdown: Record<string, unknown>;
  suggestions: Array<{ item_name: string; current_cost: number; suggestion: string }>;
  created_at: string;
}

export interface CostSimulateResult {
  analysis_id: string;
  menu_plan_id: string;
  headcount: number;
  target_cost_per_meal: number;
  estimated_cost_per_meal: number;
  estimated_cost: number;
  target_cost: number;
  variance_pct: number;
  alert_triggered: string;
  cost_breakdown: Array<{
    item_name: string;
    quantity: number;
    unit: string;
    unit_price: number;
    subtotal: number;
  }>;
  suggestions: Array<{ item_name: string; current_cost: number; suggestion: string }>;
}

export function useCostAnalyses(params: { menuPlanId?: string } = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["cost-analyses", siteId, params.menuPlanId],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      if (params.menuPlanId) qs.set("menu_plan_id", params.menuPlanId);
      return http<{ data: CostAnalysis[]; meta: unknown }>(`/cost/analyses?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useSimulateCost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      menu_plan_id: string;
      target_cost_per_meal: number;
      headcount: number;
      suggest_alternatives?: boolean;
    }) =>
      http<CostSimulateResult>("/cost/simulate", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cost-analyses"] });
    },
  });
}

export function useCostTrend(periodDays = 90) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["cost-trend", siteId, periodDays],
    queryFn: async () => {
      const qs = new URLSearchParams({
        site_id: siteId!,
        period_days: String(periodDays),
      });
      return http<{
        site_id: string;
        period_days: number;
        trend: Array<{
          date: string;
          estimated_cost: number | null;
          actual_cost: number | null;
          variance_pct: number | null;
          alert_triggered: string | null;
        }>;
        avg_variance_pct: number | null;
      }>(`/cost/trend?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useCostAnalysis(analysisId: string | undefined) {
  return useQuery({
    queryKey: ["cost-analysis", analysisId],
    queryFn: () => http<CostAnalysis>(`/cost/analyses/${analysisId}`),
    enabled: !!analysisId,
  });
}
