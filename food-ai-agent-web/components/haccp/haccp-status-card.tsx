"use client";

import { cn } from "@/lib/utils/cn";

interface HaccpStatusCardProps {
  title: string;
  value: number;
  total?: number;
  status: "success" | "warning" | "danger" | "neutral";
  subtitle?: string;
}

const STATUS_COLORS = {
  success: "border-green-200 bg-green-50 text-green-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-border bg-card text-foreground",
};

export function HaccpStatusCard({ title, value, total, status, subtitle }: HaccpStatusCardProps) {
  return (
    <div className={cn("rounded-lg border p-4", STATUS_COLORS[status])}>
      <h3 className="text-sm font-medium opacity-80">{title}</h3>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-3xl font-bold">{value}</span>
        {total !== undefined && (
          <span className="text-sm opacity-60">/ {total}</span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs opacity-70">{subtitle}</p>}
      {total !== undefined && total > 0 && (
        <div className="mt-2 h-1.5 rounded-full bg-black/10">
          <div
            className="h-full rounded-full bg-current opacity-60"
            style={{ width: `${Math.min((value / total) * 100, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}
