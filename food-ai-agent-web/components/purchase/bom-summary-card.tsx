"use client";

import type { Bom } from "@/types";

const BOM_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: "초안", color: "text-gray-500" },
  ready: { label: "준비완료", color: "text-blue-600" },
  ordered: { label: "발주됨", color: "text-green-600" },
  partial: { label: "부분발주", color: "text-amber-600" },
  complete: { label: "완료", color: "text-purple-600" },
};

interface BomSummaryCardProps {
  bom: Bom;
  onGeneratePO?: (bomId: string) => void;
}

export function BomSummaryCard({ bom, onGeneratePO }: BomSummaryCardProps) {
  const statusConfig = BOM_STATUS_LABELS[bom.status] ?? BOM_STATUS_LABELS.draft;
  const orderItemsCount = bom.items?.filter((bi) => bi.order_quantity > 0).length ?? 0;
  const totalItemsCount = bom.items?.length ?? 0;

  return (
    <div className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">BOM</p>
          <p className="mt-1 text-lg font-semibold">
            {bom.period_start} ~ {bom.period_end}
          </p>
        </div>
        <span className={`text-sm font-medium ${statusConfig.color}`}>
          {statusConfig.label}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
        <div className="rounded-md bg-muted/50 p-3 text-center">
          <p className="text-xs text-muted-foreground">식수</p>
          <p className="mt-1 text-base font-bold">{bom.headcount.toLocaleString()}명</p>
        </div>
        <div className="rounded-md bg-muted/50 p-3 text-center">
          <p className="text-xs text-muted-foreground">예상 원가</p>
          <p className="mt-1 text-base font-bold text-primary">
            {bom.total_cost.toLocaleString()}원
          </p>
        </div>
        <div className="rounded-md bg-muted/50 p-3 text-center">
          <p className="text-xs text-muted-foreground">식당 원가</p>
          <p className="mt-1 text-base font-bold">
            {bom.cost_per_meal ? `${bom.cost_per_meal.toLocaleString()}원` : "-"}
          </p>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
        <span>전체 품목: {totalItemsCount}개</span>
        <span>발주 필요: {orderItemsCount}개</span>
      </div>

      {bom.ai_summary && (
        <div className="mt-3 rounded-md bg-blue-50 p-2.5 text-xs text-blue-700">
          {bom.ai_summary}
        </div>
      )}

      {onGeneratePO && bom.status === "draft" && (
        <button
          onClick={() => onGeneratePO(bom.id)}
          className="mt-4 w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          발주서 생성
        </button>
      )}
    </div>
  );
}
