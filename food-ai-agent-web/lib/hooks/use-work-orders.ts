"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import type { WorkOrder, PaginatedResponse } from "@/types";

interface ListParams {
  page?: number;
  per_page?: number;
  date?: string;
  status?: string;
}

export function useWorkOrders(params: ListParams = {}) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { page = 1, per_page = 20, date, status } = params;

  return useQuery({
    queryKey: ["work-orders", siteId, page, per_page, date, status],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (siteId) qs.set("site_id", siteId);
      if (date) qs.set("date", date);
      if (status) qs.set("status", status);
      const res = await http<PaginatedResponse<WorkOrder>>(`/work-orders?${qs}`);
      return res as unknown as PaginatedResponse<WorkOrder>;
    },
    enabled: !!siteId,
  });
}

export function useWorkOrder(orderId: string | undefined) {
  return useQuery({
    queryKey: ["work-order", orderId],
    queryFn: () => http<WorkOrder>(`/work-orders/${orderId}`),
    enabled: !!orderId,
  });
}

export function useGenerateWorkOrders() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { menu_plan_id: string }) =>
      http<WorkOrder[]>("/work-orders/generate", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["work-orders"] });
    },
  });
}

export function useUpdateWorkOrderStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orderId, status }: { orderId: string; status: string }) =>
      http<WorkOrder>(`/work-orders/${orderId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["work-order", variables.orderId] });
      queryClient.invalidateQueries({ queryKey: ["work-orders"] });
    },
  });
}
