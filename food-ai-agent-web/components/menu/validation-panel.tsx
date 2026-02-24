"use client";

import { cn } from "@/lib/utils/cn";

interface DayResult {
  totals: Record<string, number>;
  status: "pass" | "warning" | "fail";
  violations: string[];
}

interface ValidationPanelProps {
  policyName: string;
  overallStatus: "pass" | "warning" | "fail";
  dailyResults: Record<string, DayResult>;
}

const STATUS_CONFIG = {
  pass: { label: "Pass", icon: "\u2713", color: "text-green-600 bg-green-50 border-green-200" },
  warning: { label: "Warning", icon: "\u26A0", color: "text-amber-600 bg-amber-50 border-amber-200" },
  fail: { label: "Fail", icon: "\u2717", color: "text-red-600 bg-red-50 border-red-200" },
};

export function ValidationPanel({ policyName, overallStatus, dailyResults }: ValidationPanelProps) {
  const overall = STATUS_CONFIG[overallStatus];

  return (
    <div className="rounded-lg border p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Nutrition Validation</h3>
        <span className={cn("rounded-full border px-3 py-1 text-xs font-medium", overall.color)}>
          {overall.icon} {overall.label}
        </span>
      </div>

      <p className="mb-3 text-xs text-muted-foreground">Policy: {policyName}</p>

      <div className="space-y-2">
        {Object.entries(dailyResults).map(([day, result]) => {
          const cfg = STATUS_CONFIG[result.status];
          return (
            <div key={day} className={cn("rounded border p-2", cfg.color)}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{day}</span>
                <span className="text-xs">
                  {cfg.icon} {cfg.label}
                </span>
              </div>
              <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                <span>{result.totals.kcal?.toLocaleString()}kcal</span>
                <span>Protein: {result.totals.protein}g</span>
                <span>Na: {result.totals.sodium?.toLocaleString()}mg</span>
              </div>
              {result.violations.length > 0 && (
                <ul className="mt-1 text-xs">
                  {result.violations.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
