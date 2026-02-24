"use client";

import { useQuery } from "@tanstack/react-query";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";

interface DashboardOverview {
  menu_status: Record<string, number>;
  haccp: {
    total: number;
    completed: number;
    overdue: number;
    in_progress: number;
    completion_rate: number;
  };
  work_orders: {
    total: number;
    completed: number;
    completion_rate: number;
  };
  weekly: {
    menu_confirmed: number;
    menu_total: number;
    confirmation_rate: number;
  };
  recent_activity: {
    id: string;
    action: string;
    entity_type: string;
    reason: string | null;
    created_at: string | null;
  }[];
}

interface Alert {
  type: string;
  severity: string;
  message: string;
  count: number;
}

export function useDashboardOverview() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["dashboard-overview", siteId],
    queryFn: async () => {
      const qs = siteId ? `?site_id=${siteId}` : "";
      return http<DashboardOverview>(`/dashboard/overview${qs}`);
    },
    enabled: !!siteId,
    refetchInterval: 30000,
  });
}

export function useAlerts() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["dashboard-alerts", siteId],
    queryFn: async () => {
      const qs = siteId ? `?site_id=${siteId}` : "";
      return http<Alert[]>(`/dashboard/alerts${qs}`);
    },
    enabled: !!siteId,
    refetchInterval: 30000,
  });
}

interface PurchaseSummary {
  draft: number;
  submitted: number;
  approved: number;
  received: number;
  cancelled: number;
  total: number;
  today_deliveries: number;
}

export function usePurchaseSummary() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["dashboard-purchase-summary", siteId],
    queryFn: async () => {
      const qs = siteId ? `?site_id=${siteId}` : "";
      return http<PurchaseSummary>(`/dashboard/purchase-summary${qs}`);
    },
    enabled: !!siteId,
    refetchInterval: 60000,
  });
}

interface PriceAlert {
  item_id: string;
  item_name: string;
  vendor_name: string;
  change_pct: number;
  current_price: number;
  previous_price: number;
  unit: string;
}

export function usePriceAlerts() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["dashboard-price-alerts", siteId],
    queryFn: async () => {
      const qs = siteId ? `?site_id=${siteId}&threshold=10` : "?threshold=10";
      return http<PriceAlert[]>(`/dashboard/price-alerts${qs}`);
    },
    enabled: !!siteId,
    refetchInterval: 300000,
  });
}

interface InventoryRisks {
  low_stock_count: number;
  expiry_alert_count: number;
  critical_count: number;
  risk_level: "low" | "medium" | "high" | "critical";
}

export function useInventoryRisks() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  return useQuery({
    queryKey: ["dashboard-inventory-risks", siteId],
    queryFn: async () => {
      const qs = siteId ? `?site_id=${siteId}` : "";
      return http<InventoryRisks>(`/dashboard/inventory-risks${qs}`);
    },
    enabled: !!siteId,
    refetchInterval: 60000,
  });
}
