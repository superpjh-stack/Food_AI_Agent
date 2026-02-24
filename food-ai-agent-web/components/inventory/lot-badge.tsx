"use client";

import { cn } from "@/lib/utils/cn";
import type { LotStatus } from "@/types";

const LOT_STATUS_CONFIG: Record<LotStatus, { label: string; className: string }> = {
  active: { label: "정상", className: "bg-green-100 text-green-700" },
  partially_used: { label: "부분사용", className: "bg-blue-100 text-blue-700" },
  fully_used: { label: "소진", className: "bg-gray-100 text-gray-500" },
  expired: { label: "유통기한초과", className: "bg-red-100 text-red-700" },
  rejected: { label: "반품", className: "bg-amber-100 text-amber-700" },
};

interface LotBadgeProps {
  status: LotStatus;
  className?: string;
}

export function LotBadge({ status, className }: LotBadgeProps) {
  const config = LOT_STATUS_CONFIG[status] ?? LOT_STATUS_CONFIG.active;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
