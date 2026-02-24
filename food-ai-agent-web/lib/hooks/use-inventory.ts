"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import type { Inventory, InventoryLot, PaginatedResponse } from "@/types";

interface InventoryListParams {
  page?: number;
  per_page?: number;
  category?: string;
  low_stock_only?: boolean;
}

export function useInventory(params: InventoryListParams = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { page = 1, per_page = 50, category, low_stock_only } = params;

  return useQuery({
    queryKey: ["inventory", siteId, page, per_page, category, low_stock_only],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (siteId) qs.set("site_id", siteId);
      if (category) qs.set("category", category);
      if (low_stock_only) qs.set("low_stock_only", "true");
      const res = await http<PaginatedResponse<Inventory>>(`/inventory?${qs}`);
      return res as unknown as PaginatedResponse<Inventory>;
    },
    enabled: !!siteId,
  });
}

export function useInventoryLots(params: {
  site_id?: string;
  item_id?: string;
  status?: string;
  expiry_before?: string;
  page?: number;
  per_page?: number;
} = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const effectiveSiteId = params.site_id ?? siteId;
  const { page = 1, per_page = 50 } = params;

  return useQuery({
    queryKey: ["inventory-lots", effectiveSiteId, params],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (effectiveSiteId) qs.set("site_id", effectiveSiteId);
      if (params.item_id) qs.set("item_id", params.item_id);
      if (params.status) qs.set("status", params.status);
      if (params.expiry_before) qs.set("expiry_before", params.expiry_before);
      const res = await http<PaginatedResponse<InventoryLot>>(`/inventory/lots?${qs}`);
      return res as unknown as PaginatedResponse<InventoryLot>;
    },
    enabled: !!effectiveSiteId,
  });
}

export function useInventoryLot(lotId: string | undefined) {
  return useQuery({
    queryKey: ["inventory-lot", lotId],
    queryFn: () => http<InventoryLot>(`/inventory/lots/${lotId}`),
    enabled: !!lotId,
  });
}

export function useExpiryAlerts(alertDays = 7) {
  const siteId = useSiteStore((s) => s.currentSite?.id);

  return useQuery({
    queryKey: ["expiry-alerts", siteId, alertDays],
    queryFn: async () => {
      const qs = new URLSearchParams({ alert_days: String(alertDays) });
      if (siteId) qs.set("site_id", siteId);
      return http<{
        critical: InventoryLot[];
        warning: InventoryLot[];
        total_alerts: number;
        critical_count: number;
        warning_count: number;
      }>(`/inventory/expiry-alert?${qs}`);
    },
    enabled: !!siteId,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

export function useAdjustInventory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      siteId,
      quantity,
      reason,
    }: {
      itemId: string;
      siteId: string;
      quantity: number;
      reason?: string;
    }) =>
      http<unknown>(`/inventory/${itemId}?site_id=${siteId}`, {
        method: "PUT",
        body: JSON.stringify({ quantity, reason }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}

export function useReceiveInventory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      site_id: string;
      vendor_id?: string;
      po_id?: string;
      received_at?: string;
      items: Array<{
        item_id: string;
        item_name: string;
        received_qty: number;
        unit: string;
        unit_cost?: number;
        lot_number?: string;
        expiry_date?: string;
        storage_temp?: number;
        inspect_passed?: boolean;
        inspect_note?: string;
      }>;
    }) =>
      http<unknown>("/inventory/receive", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-lots"] });
    },
  });
}

export function useTraceLot() {
  return useMutation({
    mutationFn: (lotId: string) =>
      http<unknown>(`/inventory/lots/${lotId}/trace`, { method: "POST" }),
  });
}
