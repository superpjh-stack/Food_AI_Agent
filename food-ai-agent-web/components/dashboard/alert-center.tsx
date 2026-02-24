"use client";

import { cn } from "@/lib/utils/cn";

interface Alert {
  type: string;
  severity: string;
  message: string;
  count: number;
}

interface AlertCenterProps {
  alerts: Alert[];
}

const SEVERITY_STYLES: Record<string, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
};

const TYPE_ICONS: Record<string, string> = {
  haccp_overdue: "\u26A0",
  menu_review: "\uD83D\uDCCB",
  incident_open: "\uD83D\uDEA8",
};

export function AlertCenter({ alerts }: AlertCenterProps) {
  if (!alerts.length) {
    return (
      <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        No active alerts.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert, idx) => (
        <div
          key={idx}
          className={cn(
            "flex items-center gap-3 rounded-lg border p-3",
            SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.info,
          )}
        >
          <span className="text-lg">{TYPE_ICONS[alert.type] ?? "\u2139"}</span>
          <span className="flex-1 text-sm font-medium">{alert.message}</span>
          <span className="rounded-full bg-white/50 px-2 py-0.5 text-xs font-bold">
            {alert.count}
          </span>
        </div>
      ))}
    </div>
  );
}
