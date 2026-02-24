"use client";

import { useState } from "react";
import Link from "next/link";
import { useBoms } from "@/lib/hooks/use-boms";
import { usePurchaseOrders } from "@/lib/hooks/use-purchase-orders";
import { BomSummaryCard } from "@/components/purchase/bom-summary-card";
import { PurchaseOrderTable } from "@/components/purchase/purchase-order-table";
import type { POStatus } from "@/types";

const STATUS_TABS: { label: string; value: POStatus | "all" }[] = [
  { label: "전체", value: "all" },
  { label: "초안", value: "draft" },
  { label: "제출됨", value: "submitted" },
  { label: "승인됨", value: "approved" },
  { label: "수령완료", value: "received" },
];

export default function PurchasePage() {
  const [activeStatus, setActiveStatus] = useState<POStatus | "all">("all");
  const [activeTab, setActiveTab] = useState<"boms" | "orders">("orders");

  const { data: bomsData, isLoading: bomsLoading } = useBoms({ per_page: 10 });
  const { data: poData, isLoading: poLoading } = usePurchaseOrders({
    status: activeStatus === "all" ? undefined : activeStatus,
  });

  const boms = bomsData?.data ?? [];
  const orders = poData?.data ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">BOM & 발주 관리</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            소요량 산출(BOM)과 발주서를 관리합니다.
          </p>
        </div>
        <Link
          href="/purchase/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          발주서 직접 생성
        </Link>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 rounded-lg border bg-muted/30 p-1">
        <button
          onClick={() => setActiveTab("orders")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "orders"
              ? "bg-background shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          발주서 목록
        </button>
        <button
          onClick={() => setActiveTab("boms")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "boms"
              ? "bg-background shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          BOM 목록
        </button>
      </div>

      {/* Purchase Orders Tab */}
      {activeTab === "orders" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setActiveStatus(tab.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  activeStatus === tab.value
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <PurchaseOrderTable orders={orders} isLoading={poLoading} />

          <div className="text-right text-sm text-muted-foreground">
            총 {poData?.meta.total ?? 0}건
          </div>
        </div>
      )}

      {/* BOMs Tab */}
      {activeTab === "boms" && (
        <div className="space-y-4">
          {bomsLoading ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
              로딩 중...
            </div>
          ) : boms.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed p-10 text-center text-muted-foreground">
              <p className="text-sm">BOM이 없습니다.</p>
              <p className="mt-1 text-xs">식단 확정 시 BOM이 자동 생성됩니다.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {boms.map((bom) => (
                <BomSummaryCard key={bom.id} bom={bom} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
