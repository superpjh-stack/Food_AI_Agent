"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";

export interface DemandForecast {
  id: string;
  site_id: string;
  forecast_date: string;
  meal_type: string;
  predicted_min: number;
  predicted_mid: number;
  predicted_max: number;
  confidence_pct: number;
  risk_factors: string[];
  model_used: string;
  generated_at: string;
}

export interface ActualHeadcount {
  id: string;
  site_id: string;
  record_date: string;
  meal_type: string;
  planned: number;
  actual: number;
  served: number | null;
  notes: string | null;
  recorded_at: string;
}

export interface SiteEvent {
  id: string;
  site_id: string;
  event_date: string;
  event_type: string;
  event_name: string | null;
  adjustment_factor: number;
  affects_meal_types: string[];
  notes: string | null;
  created_at: string;
}

export function useForecastList(params: {
  dateFrom?: string;
  dateTo?: string;
  mealType?: string;
  page?: number;
  perPage?: number;
} = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { dateFrom, dateTo, mealType, page = 1, perPage = 20 } = params;

  return useQuery({
    queryKey: ["forecasts", siteId, dateFrom, dateTo, mealType, page, perPage],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(perPage) });
      if (siteId) qs.set("site_id", siteId);
      if (dateFrom) qs.set("date_from", dateFrom);
      if (dateTo) qs.set("date_to", dateTo);
      if (mealType) qs.set("meal_type", mealType);
      return http<{ data: DemandForecast[]; meta: unknown }>(`/forecast/headcount?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useCreateForecast() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      forecast_date: string;
      meal_type: string;
      model?: string;
    }) =>
      http<DemandForecast>("/forecast/headcount", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forecasts"] });
    },
  });
}

export function useRecordActual() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      record_date: string;
      meal_type: string;
      planned: number;
      actual: number;
      served?: number;
      notes?: string;
    }) =>
      http<ActualHeadcount>("/forecast/actual", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["actuals"] });
    },
  });
}

export function useActualList(params: { dateFrom?: string; dateTo?: string } = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["actuals", siteId, params.dateFrom, params.dateTo],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      if (params.dateFrom) qs.set("date_from", params.dateFrom);
      if (params.dateTo) qs.set("date_to", params.dateTo);
      return http<{ data: ActualHeadcount[]; meta: unknown }>(`/forecast/actual?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useSiteEvents(params: { dateFrom?: string; dateTo?: string } = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["site-events", siteId, params.dateFrom, params.dateTo],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      if (params.dateFrom) qs.set("date_from", params.dateFrom);
      if (params.dateTo) qs.set("date_to", params.dateTo);
      return http<SiteEvent[]>(`/forecast/site-events?${qs}`);
    },
    enabled: !!siteId,
  });
}

export function useCreateSiteEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      site_id: string;
      event_date: string;
      event_type: string;
      event_name?: string;
      adjustment_factor?: number;
      affects_meal_types?: string[];
      notes?: string;
    }) =>
      http<SiteEvent>("/forecast/site-events", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["site-events"] });
    },
  });
}

export function useDeleteSiteEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      http<unknown>(`/forecast/site-events/${eventId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["site-events"] });
    },
  });
}
