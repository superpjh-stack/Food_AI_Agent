"use client";

import { cn } from "@/lib/utils/cn";

interface ResponseStep {
  step: number;
  action: string;
  done: boolean;
}

interface IncidentResponseStepsProps {
  steps: ResponseStep[];
  severity: string;
  onToggle?: (stepIndex: number) => void;
}

const SEVERITY_HEADER: Record<string, { text: string; color: string }> = {
  low: { text: "Low Severity", color: "bg-gray-100 text-gray-700 border-gray-200" },
  medium: { text: "Medium Severity", color: "bg-amber-100 text-amber-700 border-amber-200" },
  high: { text: "High Severity", color: "bg-orange-100 text-orange-700 border-orange-200" },
  critical: { text: "CRITICAL", color: "bg-red-100 text-red-700 border-red-200" },
};

export function IncidentResponseSteps({ steps, severity, onToggle }: IncidentResponseStepsProps) {
  const header = SEVERITY_HEADER[severity] ?? SEVERITY_HEADER.medium;
  const completedCount = steps.filter((s) => s.done).length;

  return (
    <div className="rounded-lg border p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Immediate Response Steps</h3>
        <span className={cn("rounded-full border px-3 py-0.5 text-xs font-medium", header.color)}>
          {header.text}
        </span>
      </div>

      {/* Progress */}
      <div className="mb-3 flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${(completedCount / steps.length) * 100}%` }}
          />
        </div>
        <span className="text-xs text-muted-foreground">
          {completedCount}/{steps.length}
        </span>
      </div>

      <ol className="space-y-2">
        {steps.map((step, idx) => (
          <li key={step.step}>
            <button
              onClick={() => onToggle?.(idx)}
              disabled={!onToggle}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors",
                step.done ? "border-green-200 bg-green-50" : "border-border hover:bg-muted/30",
              )}
            >
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                  step.done ? "bg-green-500 text-white" : "bg-muted text-muted-foreground",
                )}
              >
                {step.done ? "\u2713" : step.step}
              </span>
              <span className={cn("flex-1 text-sm", step.done && "text-muted-foreground line-through")}>
                {step.action}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
