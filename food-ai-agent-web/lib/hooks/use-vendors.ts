"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import type { Vendor, VendorPrice, PaginatedResponse } from "@/types";

interface ListParams {
  page?: number;
  per_page?: number;
  category?: string;
  is_active?: boolean;
}

export function useVendors(params: ListParams = {}) {
  const { page = 1, per_page = 20, category, is_active } = params;

  return useQuery({
    queryKey: ["vendors", page, per_page, category, is_active],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (category) qs.set("category", category);
      if (is_active !== undefined) qs.set("is_active", String(is_active));
      const res = await http<PaginatedResponse<Vendor>>(`/vendors?${qs}`);
      return res as unknown as PaginatedResponse<Vendor>;
    },
  });
}

export function useVendor(vendorId: string | undefined) {
  return useQuery({
    queryKey: ["vendor", vendorId],
    queryFn: () => http<Vendor>(`/vendors/${vendorId}`),
    enabled: !!vendorId,
  });
}

export function useVendorPrices(
  vendorId: string | undefined,
  params: { item_id?: string; is_current?: boolean } = {}
) {
  return useQuery({
    queryKey: ["vendor-prices", vendorId, params],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (params.item_id) qs.set("item_id", params.item_id);
      if (params.is_current !== undefined) qs.set("is_current", String(params.is_current));
      const res = await http<PaginatedResponse<VendorPrice>>(
        `/vendors/${vendorId}/prices?${qs}`
      );
      return res as unknown as PaginatedResponse<VendorPrice>;
    },
    enabled: !!vendorId,
  });
}

export function useItemVendors(itemId: string | undefined, siteId?: string) {
  return useQuery({
    queryKey: ["item-vendors", itemId, siteId],
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (siteId) qs.set("site_id", siteId);
      return http<{ data: unknown[]; meta: { best_price: number | null } }>(
        `/vendors/items/${itemId}/vendors?${qs}`
      );
    },
    enabled: !!itemId,
  });
}

export function useCreateVendor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      business_no?: string;
      contact?: Record<string, string>;
      categories?: string[];
      lead_days?: number;
      rating?: number;
      notes?: string;
    }) =>
      http<Vendor>("/vendors", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
    },
  });
}

export function useUpdateVendor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ vendorId, data }: { vendorId: string; data: Partial<Vendor> }) =>
      http<Vendor>(`/vendors/${vendorId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["vendor", variables.vendorId] });
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
    },
  });
}

export function useUpsertVendorPrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      vendorId,
      data,
    }: {
      vendorId: string;
      data: {
        item_id: string;
        unit_price: number;
        unit: string;
        effective_from: string;
        site_id?: string;
      };
    }) =>
      http<VendorPrice>(`/vendors/${vendorId}/prices`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["vendor-prices", variables.vendorId] });
    },
  });
}
