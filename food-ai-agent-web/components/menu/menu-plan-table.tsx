"use client";

import Link from "next/link";
import { cn } from "@/lib/utils/cn";
import type { MenuPlan } from "@/types";

interface MenuPlanTableProps {
  plans: MenuPlan[];
  isLoading?: boolean;
}

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-gray-100 text-gray-700" },
  review: { label: "Review", className: "bg-blue-100 text-blue-700" },
  confirmed: { label: "Confirmed", className: "bg-green-100 text-green-700" },
  archived: { label: "Archived", className: "bg-muted text-muted-foreground" },
};

export function MenuPlanTable({ plans, isLoading }: MenuPlanTableProps) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (plans.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        No menu plans found. Create one to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">Title</th>
            <th className="px-4 py-3 text-left font-medium">Period</th>
            <th className="px-4 py-3 text-left font-medium">Headcount</th>
            <th className="px-4 py-3 text-left font-medium">Status</th>
            <th className="px-4 py-3 text-left font-medium">Version</th>
          </tr>
        </thead>
        <tbody>
          {plans.map((plan) => {
            const status = STATUS_STYLES[plan.status] ?? STATUS_STYLES.draft;
            return (
              <tr key={plan.id} className="border-b last:border-0 hover:bg-muted/30">
                <td className="px-4 py-3">
                  <Link
                    href={`/menu-studio/${plan.id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {plan.title ?? "Untitled"}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {plan.period_start} ~ {plan.period_end}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {plan.target_headcount?.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", status.className)}>
                    {status.label}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">v{plan.version}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
