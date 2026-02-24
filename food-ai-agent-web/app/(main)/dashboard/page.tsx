"use client";

import {
  useDashboardOverview,
  useAlerts,
  usePurchaseSummary,
  usePriceAlerts,
  useInventoryRisks,
} from "@/lib/hooks/use-dashboard";
import { OverviewCards } from "@/components/dashboard/overview-cards";
import { WeeklyStatus } from "@/components/dashboard/weekly-status";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { AlertCenter } from "@/components/dashboard/alert-center";
import { PurchaseStatusWidget } from "@/components/dashboard/purchase-status-widget";
import { PriceAlertWidget } from "@/components/dashboard/price-alert-widget";
import { InventoryRiskWidget } from "@/components/dashboard/inventory-risk-widget";

export default function DashboardPage() {
  const { data: overview, isLoading } = useDashboardOverview();
  const { data: alerts } = useAlerts();
  const { data: purchaseSummary, isLoading: purchaseLoading } = usePurchaseSummary();
  const { data: priceAlerts, isLoading: priceLoading } = usePriceAlerts();
  const { data: inventoryRisks, isLoading: inventoryLoading } = useInventoryRisks();

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        Loading dashboard...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Operational overview for today
        </p>
      </div>

      {/* Alerts */}
      {alerts && alerts.length > 0 && (
        <AlertCenter alerts={alerts} />
      )}

      {/* KPI Cards */}
      {overview && (
        <OverviewCards
          menuStatus={overview.menu_status}
          haccpCompletionRate={overview.haccp.completion_rate}
          workOrderCompletionRate={overview.work_orders.completion_rate}
        />
      )}

      {/* MVP2 Purchase & Inventory Widgets */}
      <div className="grid gap-4 md:grid-cols-3">
        <PurchaseStatusWidget
          draft={purchaseSummary?.draft ?? 0}
          submitted={purchaseSummary?.submitted ?? 0}
          approved={purchaseSummary?.approved ?? 0}
          received={purchaseSummary?.received ?? 0}
          todayDeliveries={purchaseSummary?.today_deliveries ?? 0}
        />
        <PriceAlertWidget
          alerts={priceAlerts ?? []}
          isLoading={priceLoading}
        />
        <InventoryRiskWidget
          lowStockCount={inventoryRisks?.low_stock_count ?? 0}
          expiryAlertCount={inventoryRisks?.expiry_alert_count ?? 0}
          criticalCount={inventoryRisks?.critical_count ?? 0}
          riskLevel={inventoryRisks?.risk_level ?? "low"}
          isLoading={inventoryLoading}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Weekly Status */}
        {overview && (
          <WeeklyStatus
            menuConfirmed={overview.weekly.menu_confirmed}
            menuTotal={overview.weekly.menu_total}
            confirmationRate={overview.weekly.confirmation_rate}
          />
        )}

        {/* Activity Feed */}
        {overview && (
          <ActivityFeed activities={overview.recent_activity} />
        )}
      </div>
    </div>
  );
}
