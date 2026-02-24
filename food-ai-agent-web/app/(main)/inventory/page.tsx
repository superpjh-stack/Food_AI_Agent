"use client";

import { useState } from "react";
import Link from "next/link";
import { useInventory } from "@/lib/hooks/use-inventory";
import { useExpiryAlerts } from "@/lib/hooks/use-inventory";
import { InventoryGrid } from "@/components/inventory/inventory-grid";
import { ExpiryAlertList } from "@/components/inventory/expiry-alert-list";

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<"grid" | "expiry">("grid");
  const [category, setCategory] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);

  const { data: inventoryData, isLoading } = useInventory({
    category: category || undefined,
    low_stock_only: lowStockOnly,
  });

  const { data: expiryData, isLoading: expiryLoading } = useExpiryAlerts(7);

  const items = inventoryData?.data ?? [];
  const expiryAlerts = expiryData?.data ?? { critical: [], warning: [], total_alerts: 0 };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">재고 현황</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            식재료 재고와 유통기한을 관리합니다.
          </p>
        </div>
        <Link
          href="/inventory/receive"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          입고 검수
        </Link>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-xs text-muted-foreground">전체 품목</p>
          <p className="mt-1 text-2xl font-bold">{inventoryData?.meta.total ?? 0}</p>
        </div>
        <div className="rounded-lg border bg-red-50 p-4 text-center">
          <p className="text-xs text-red-600">재고 부족</p>
          <p className="mt-1 text-2xl font-bold text-red-700">
            {items.filter((i) => i.is_low_stock).length}
          </p>
        </div>
        <div className="rounded-lg border bg-amber-50 p-4 text-center">
          <p className="text-xs text-amber-600">유통기한 임박</p>
          <p className="mt-1 text-2xl font-bold text-amber-700">
            {expiryAlerts.total_alerts}
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 rounded-lg border bg-muted/30 p-1">
        <button
          onClick={() => setActiveTab("grid")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "grid"
              ? "bg-background shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          재고 현황
        </button>
        <button
          onClick={() => setActiveTab("expiry")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "expiry"
              ? "bg-background shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          유통기한 알림
          {expiryAlerts.total_alerts > 0 && (
            <span className="ml-1.5 rounded-full bg-red-500 px-1.5 py-0.5 text-xs text-white">
              {expiryAlerts.total_alerts}
            </span>
          )}
        </button>
      </div>

      {/* Inventory Grid Tab */}
      {activeTab === "grid" && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="카테고리 필터 (채소, 육류...)"
              className="rounded-md border bg-background px-3 py-2 text-sm"
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={lowStockOnly}
                onChange={(e) => setLowStockOnly(e.target.checked)}
                className="h-4 w-4"
              />
              재고 부족만 보기
            </label>
          </div>
          <InventoryGrid items={items} isLoading={isLoading} />
        </div>
      )}

      {/* Expiry Alerts Tab */}
      {activeTab === "expiry" && (
        <ExpiryAlertList
          critical={expiryAlerts.critical as any}
          warning={expiryAlerts.warning as any}
          isLoading={expiryLoading}
        />
      )}
    </div>
  );
}
