"use client";

interface CostVarianceIndicatorProps {
  variancePct: number;
  alertTriggered: string;
}

export function CostVarianceIndicator({ variancePct, alertTriggered }: CostVarianceIndicatorProps) {
  const absVariance = Math.abs(variancePct);
  const isOver = variancePct > 0;

  const colorClass =
    alertTriggered === "critical"
      ? "bg-red-500"
      : alertTriggered === "warning"
      ? "bg-yellow-400"
      : "bg-green-500";

  const labelClass =
    alertTriggered === "critical"
      ? "text-red-700"
      : alertTriggered === "warning"
      ? "text-yellow-700"
      : "text-green-700";

  const barWidth = Math.min(absVariance, 30);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">목표 대비 편차</span>
        <span className={`font-semibold ${labelClass}`}>
          {isOver ? "+" : ""}{variancePct.toFixed(1)}%{" "}
          {alertTriggered !== "none" && `(${alertTriggered})`}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200">
        <div
          className={`h-2 rounded-full transition-all ${colorClass}`}
          style={{ width: `${(barWidth / 30) * 100}%` }}
        />
      </div>
    </div>
  );
}
