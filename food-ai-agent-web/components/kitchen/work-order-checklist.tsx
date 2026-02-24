"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";
import type { WorkOrder } from "@/types";

interface WorkOrderChecklistProps {
  order: WorkOrder;
  onComplete: () => void;
  onStart: () => void;
}

export function WorkOrderChecklist({ order, onComplete, onStart }: WorkOrderChecklistProps) {
  const [checkedSteps, setCheckedSteps] = useState<Set<number>>(new Set());

  const toggleStep = (stepOrder: number) => {
    setCheckedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepOrder)) next.delete(stepOrder);
      else next.add(stepOrder);
      return next;
    });
  };

  const allDone = checkedSteps.size === order.steps.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{order.recipe_name}</h3>
        <span className="text-sm text-muted-foreground">
          {checkedSteps.size} / {order.steps.length} steps
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${(checkedSteps.size / order.steps.length) * 100}%` }}
        />
      </div>

      {/* Steps */}
      <ol className="space-y-2">
        {order.steps.map((step) => {
          const checked = checkedSteps.has(step.order);
          return (
            <li key={step.order}>
              <button
                onClick={() => toggleStep(step.order)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors",
                  checked ? "border-green-200 bg-green-50" : "hover:bg-muted/30",
                )}
              >
                <span
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                    checked
                      ? "bg-green-500 text-white"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {checked ? "\u2713" : step.order}
                </span>
                <div className="flex-1">
                  <p className={cn("text-sm", checked && "text-muted-foreground line-through")}>
                    {step.description}
                  </p>
                  <div className="mt-1 flex gap-2">
                    {step.duration_min && (
                      <span className="text-xs text-muted-foreground">{step.duration_min}min</span>
                    )}
                    {step.ccp && (
                      <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
                        CCP: {step.ccp.type} - {step.ccp.target}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            </li>
          );
        })}
      </ol>

      {/* Action buttons */}
      <div className="flex gap-2">
        {order.status === "pending" && (
          <button
            onClick={onStart}
            className="flex-1 rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Start Cooking
          </button>
        )}
        {order.status === "in_progress" && (
          <button
            onClick={onComplete}
            disabled={!allDone}
            className="flex-1 rounded-md bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {allDone ? "Mark Complete" : `${order.steps.length - checkedSteps.size} steps remaining`}
          </button>
        )}
      </div>
    </div>
  );
}
