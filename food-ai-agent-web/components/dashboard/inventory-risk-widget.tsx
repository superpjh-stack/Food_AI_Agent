"use client";

import Link from "next/link";

interface InventoryRiskWidgetProps {
  lowStockCount: number;
  expiryAlertCount: number;
  criticalCount: number;
  riskLevel: "low" | "medium" | "high" | "critical";
  isLoading?: boolean;
}

const RISK_CONFIG = {
  low: { label: "정상", badgeClass: "bg-green-100 text-green-700", barClass: "bg-green-500" },
  medium: { label: "주의", badgeClass: "bg-amber-100 text-amber-700", barClass: "bg-amber-500" },
  high: { label: "위험", badgeClass: "bg-orange-100 text-orange-700", barClass: "bg-orange-500" },
  critical: { label: "긴급", badgeClass: "bg-red-100 text-red-700", barClass: "bg-red-500" },
};

export function InventoryRiskWidget({
  lowStockCount,
  expiryAlertCount,
  criticalCount,
  riskLevel,
  isLoading,
}: InventoryRiskWidgetProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">재고 리스크</h3>
        <div className="mt-3 flex h-20 items-center justify-center text-xs text-muted-foreground">
          로딩 중...
        </div>
      </div>
    );
  }

  const config = RISK_CONFIG[riskLevel];
  const totalRisks = lowStockCount + expiryAlertCount;

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">재고 리스크</h3>
        <Link href="/inventory" className="text-xs text-primary hover:underline">
          재고 현황
        </Link>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${config.badgeClass}`}>
          {config.label}
        </span>
        {totalRisks > 0 && (
          <span className="text-xs text-muted-foreground">{totalRisks}건 주의 필요</span>
        )}
      </div>

      <div className="mt-3 space-y-2.5">
        <RiskRow
          label="재고 부족"
          count={lowStockCount}
          href="/inventory"
          urgency={lowStockCount > 5 ? "high" : lowStockCount > 0 ? "medium" : "none"}
        />
        <RiskRow
          label="유통기한 임박 (D-7)"
          count={expiryAlertCount}
          href="/inventory"
          urgency={expiryAlertCount > 3 ? "high" : expiryAlertCount > 0 ? "medium" : "none"}
        />
        <RiskRow
          label="유통기한 긴급 (D-3)"
          count={criticalCount}
          href="/inventory"
          urgency={criticalCount > 0 ? "critical" : "none"}
        />
      </div>

      {totalRisks === 0 && criticalCount === 0 && (
        <p className="mt-3 text-center text-xs text-green-600">모든 재고 정상</p>
      )}
    </div>
  );
}

function RiskRow({
  label,
  count,
  href,
  urgency,
}: {
  label: string;
  count: number;
  href: string;
  urgency: "none" | "medium" | "high" | "critical";
}) {
  const countClass =
    urgency === "critical"
      ? "text-red-600 font-bold"
      : urgency === "high"
      ? "text-orange-600 font-semibold"
      : urgency === "medium"
      ? "text-amber-600"
      : "text-muted-foreground";

  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <Link href={href} className={`${countClass} hover:underline`}>
        {count}건
      </Link>
    </div>
  );
}
