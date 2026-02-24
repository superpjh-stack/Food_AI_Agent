"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";

export interface WasteRecord {
  id: string;
  site_id: string;
  record_date: string;
  meal_type: string;
  item_name: string;
  recipe_id: string | null;
  waste_kg: number | null;
  waste_pct: number | null;
  served_count: number | null;
  notes: string | null;
  recorded_at: string;
}

export interface MenuPreference {
  id: string;
  site_id: string;
  recipe_id: string;
  preference_score: number;
  waste_avg_pct: number;
  serve_count: number;
  last_served: string | null;
  updated_at: string;
}

export interface WasteSummaryItem {
  item_name: string;
  recipe_id: string | null;
  avg_waste_pct: number;
  total_records: number;
}

export function useWasteRecords(params: {
  dateFrom?: string;
  dateTo?: string;
  mealType?: string;
  page?: number;
  perPage?: number;
} = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { dateFrom, dateTo, mealType, page = 1, perPage = 20 } = params;

  return useQuery({
    queryKey: ["waste-records", siteId, dateFrom, dateTo, mealType, page],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(perPage) });
      if (siteId) qs.set("site_id", siteId);
      if (dateFrom) qs.set("date_from", dateFrom);
      if (dateTo) qs.set("date_to", dateTo);
      if (mealType) qs.set("meal_type", mealType);
      return http<{ data: WasteRecord[]; meta: unknown }>(`/waste/records?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useCreateWasteRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      record_date: string;
      meal_type: string;
      items: Array<{
        item_name: string;
        waste_pct?: number;
        waste_kg?: number;
        recipe_id?: string;
        served_count?: number;
        notes?: string;
      }>;
    }) =>
      http<unknown>("/waste/records", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["waste-records"] });
      queryClient.invalidateQueries({ queryKey: ["waste-summary"] });
      queryClient.invalidateQueries({ queryKey: ["menu-preferences"] });
    },
  });
}

export function useWasteSummary(periodDays = 30) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["waste-summary", siteId, periodDays],
    queryFn: async () => {
      const qs = new URLSearchParams({ period_days: String(periodDays) });
      if (siteId) qs.set("site_id", siteId);
      return http<{
        site_id: string;
        period_days: number;
        items: WasteSummaryItem[];
        total_records: number;
      }>(`/waste/summary?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useMenuPreferences() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["menu-preferences", siteId],
    queryFn: async () => {
      return http<{ data: MenuPreference[]; meta: unknown }>(`/waste/preferences/${siteId}`);
    },
    enabled: !!siteId,
  });
}

export function useUpdateMenuPreferences() {
  const queryClient = useQueryClient();
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useMutation({
    mutationFn: (items: Array<{ recipe_id: string; preference_score: number; waste_pct?: number }>) =>
      http<unknown>(`/waste/preferences/${siteId}`, {
        method: "PUT",
        body: JSON.stringify(items),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["menu-preferences"] });
    },
  });
}
