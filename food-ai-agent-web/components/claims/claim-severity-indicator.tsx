"use client";

const SEVERITY_STYLES: Record<string, { dot: string; text: string; label: string }> = {
  low:      { dot: "bg-green-500",  text: "text-green-700",  label: "낮음" },
  medium:   { dot: "bg-yellow-500", text: "text-yellow-700", label: "보통" },
  high:     { dot: "bg-orange-500", text: "text-orange-700", label: "높음" },
  critical: { dot: "bg-red-600",    text: "text-red-700",    label: "긴급" },
};

interface ClaimSeverityIndicatorProps {
  severity: string;
  showLabel?: boolean;
}

export function ClaimSeverityIndicator({ severity, showLabel = true }: ClaimSeverityIndicatorProps) {
  const style = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.medium;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${style.text}`}>
      <span className={`h-2 w-2 rounded-full ${style.dot}`} />
      {showLabel && style.label}
    </span>
  );
}
