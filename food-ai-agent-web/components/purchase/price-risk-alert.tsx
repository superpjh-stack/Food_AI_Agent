"use client";

interface RiskItem {
  item_id: string;
  item_name?: string;
  current_price: number;
  previous_price: number;
  change_pct: number;
}

interface PriceRiskAlertProps {
  riskItems: RiskItem[];
  thresholdPct?: number;
  onViewAlternatives?: (itemId: string) => void;
}

export function PriceRiskAlert({
  riskItems,
  thresholdPct = 15,
  onViewAlternatives,
}: PriceRiskAlertProps) {
  if (riskItems.length === 0) {
    return (
      <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
        현재 단가 급등 위험 품목이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">
        <span>단가 {thresholdPct}% 이상 급등 품목</span>
        <strong>{riskItems.length}개</strong>
        <span>발견 (SAFE-PUR-002)</span>
      </div>
      {riskItems.map((item) => (
        <div
          key={item.item_id}
          className="flex items-center justify-between rounded-md border border-red-100 bg-red-50 px-4 py-3"
        >
          <div>
            <p className="font-medium text-foreground">
              {item.item_name ?? item.item_id}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {item.previous_price.toLocaleString()}원 → {item.current_price.toLocaleString()}원
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-bold text-red-700">
              +{item.change_pct}%
            </span>
            {onViewAlternatives && (
              <button
                onClick={() => onViewAlternatives(item.item_id)}
                className="text-xs text-primary hover:underline"
              >
                대체품 보기
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
