"use client";

interface WasteRateWidgetProps {
  wasteData?: {
    avg_waste_pct_7d: number | null;
  };
}

export function WasteRateWidget({ wasteData }: WasteRateWidgetProps) {
  const rate = wasteData?.avg_waste_pct_7d;

  const colorClass =
    rate == null ? "text-muted-foreground"
    : rate >= 20 ? "text-red-600"
    : rate >= 10 ? "text-yellow-600"
    : "text-green-600";

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-xs text-muted-foreground">7일 평균 잔반률</div>
      <div className={`mt-1 text-2xl font-bold ${colorClass}`}>
        {rate != null ? `${rate.toFixed(1)}%` : "N/A"}
      </div>
      <div className="text-xs text-muted-foreground">목표: 10% 이하</div>
    </div>
  );
}
