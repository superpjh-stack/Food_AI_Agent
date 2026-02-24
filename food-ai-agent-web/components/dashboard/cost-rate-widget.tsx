"use client";

interface CostRateWidgetProps {
  costData?: {
    latest_variance_pct: number | null;
    alert_triggered: string | null;
  };
}

export function CostRateWidget({ costData }: CostRateWidgetProps) {
  const variance = costData?.latest_variance_pct;
  const alert = costData?.alert_triggered;

  const colorClass =
    alert === "critical" ? "text-red-600"
    : alert === "warning" ? "text-yellow-600"
    : "text-green-600";

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-xs text-muted-foreground">원가 편차 (최근)</div>
      <div className={`mt-1 text-2xl font-bold ${colorClass}`}>
        {variance != null ? `${variance > 0 ? "+" : ""}${variance.toFixed(1)}%` : "N/A"}
      </div>
      <div className="text-xs text-muted-foreground">
        {alert === "critical" ? "초과 긴급" : alert === "warning" ? "초과 경고" : "정상 범위"}
      </div>
    </div>
  );
}
