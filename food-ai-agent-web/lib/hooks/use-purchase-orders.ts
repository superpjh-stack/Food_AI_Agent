"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import type { PurchaseOrder, PaginatedResponse } from "@/types";

interface ListParams {
  page?: number;
  per_page?: number;
  status?: string;
  vendor_id?: string;
  order_date_from?: string;
  order_date_to?: string;
}

export function usePurchaseOrders(params: ListParams = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { page = 1, per_page = 20, status, vendor_id, order_date_from, order_date_to } = params;

  return useQuery({
    queryKey: ["purchase-orders", siteId, page, per_page, status, vendor_id, order_date_from, order_date_to],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (siteId) qs.set("site_id", siteId);
      if (status) qs.set("status", status);
      if (vendor_id) qs.set("vendor_id", vendor_id);
      if (order_date_from) qs.set("order_date_from", order_date_from);
      if (order_date_to) qs.set("order_date_to", order_date_to);
      const res = await http<PaginatedResponse<PurchaseOrder>>(`/purchase-orders?${qs}`);
      return res as unknown as PaginatedResponse<PurchaseOrder>;
    },
    enabled: !!siteId,
  });
}

export function usePurchaseOrder(poId: string | undefined) {
  return useQuery({
    queryKey: ["purchase-order", poId],
    queryFn: () => http<PurchaseOrder>(`/purchase-orders/${poId}`),
    enabled: !!poId,
  });
}

export function useCreatePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      bom_id?: string;
      site_id: string;
      vendor_id: string;
      order_date: string;
      delivery_date: string;
      note?: string;
      items: unknown[];
    }) =>
      http<PurchaseOrder>("/purchase-orders", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useUpdatePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      poId,
      data,
    }: {
      poId: string;
      data: { delivery_date?: string; note?: string; items?: unknown[] };
    }) =>
      http<PurchaseOrder>(`/purchase-orders/${poId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-order", variables.poId] });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useDeletePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (poId: string) =>
      http<unknown>(`/purchase-orders/${poId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useSubmitPurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poId, note }: { poId: string; note?: string }) =>
      http<PurchaseOrder>(`/purchase-orders/${poId}/submit`, {
        method: "POST",
        body: JSON.stringify({ note }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-order", variables.poId] });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useApprovePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poId, note }: { poId: string; note?: string }) =>
      http<PurchaseOrder>(`/purchase-orders/${poId}/approve`, {
        method: "POST",
        body: JSON.stringify({ note }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-order", variables.poId] });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useCancelPurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poId, cancel_reason }: { poId: string; cancel_reason: string }) =>
      http<PurchaseOrder>(`/purchase-orders/${poId}/cancel`, {
        method: "POST",
        body: JSON.stringify({ cancel_reason }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-order", variables.poId] });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
  });
}

export function useReceivePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      poId,
      data,
    }: {
      poId: string;
      data: {
        items: Array<{
          po_item_id: string;
          received_qty: number;
          reject_reason?: string;
        }>;
        lot_number?: string;
        expiry_date?: string;
        storage_temp?: number;
        inspect_note?: string;
      };
    }) =>
      http<unknown>(`/purchase-orders/${poId}/receive`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-order", variables.poId] });
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}
