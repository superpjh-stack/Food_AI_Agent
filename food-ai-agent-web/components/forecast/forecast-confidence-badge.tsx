"use client";

interface ForecastConfidenceBadgeProps {
  confidencePct: number;
}

export function ForecastConfidenceBadge({ confidencePct }: ForecastConfidenceBadgeProps) {
  const label = `${confidencePct.toFixed(1)}%`;
  const colorClass =
    confidencePct >= 80
      ? "bg-green-100 text-green-800 border-green-200"
      : confidencePct >= 60
      ? "bg-yellow-100 text-yellow-800 border-yellow-200"
      : "bg-red-100 text-red-800 border-red-200";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${colorClass}`}
      title={`신뢰도 ${label}`}
    >
      신뢰도 {label}
    </span>
  );
}
