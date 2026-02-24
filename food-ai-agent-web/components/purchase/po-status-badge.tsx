"use client";

import { cn } from "@/lib/utils/cn";
import type { POStatus } from "@/types";

const STATUS_CONFIG: Record<POStatus, { label: string; className: string }> = {
  draft: { label: "초안", className: "bg-gray-100 text-gray-700" },
  submitted: { label: "제출됨", className: "bg-blue-100 text-blue-700" },
  approved: { label: "승인됨", className: "bg-green-100 text-green-700" },
  received: { label: "수령완료", className: "bg-purple-100 text-purple-700" },
  cancelled: { label: "취소됨", className: "bg-red-100 text-red-600" },
};

interface POStatusBadgeProps {
  status: POStatus;
  className?: string;
}

export function POStatusBadge({ status, className }: POStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
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
