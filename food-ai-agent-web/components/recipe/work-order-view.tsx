"use client";

import { cn } from "@/lib/utils/cn";
import type { WorkOrder } from "@/types";

interface WorkOrderViewProps {
  order: WorkOrder;
  onStatusChange?: (status: string) => void;
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "bg-gray-100 text-gray-700" },
  in_progress: { label: "In Progress", color: "bg-blue-100 text-blue-700" },
  completed: { label: "Completed", color: "bg-green-100 text-green-700" },
};

export function WorkOrderView({ order, onStatusChange }: WorkOrderViewProps) {
  const status = STATUS_CONFIG[order.status] ?? STATUS_CONFIG.pending;

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-medium">{order.recipe_name}</h3>
          <p className="text-sm text-muted-foreground">
            {order.date} / {order.meal_type} / {order.scaled_servings} servings
          </p>
        </div>
        <span className={cn("rounded-full px-3 py-1 text-xs font-medium", status.color)}>
          {status.label}
        </span>
      </div>

      {/* Scaled ingredients */}
      <div>
        <h4 className="mb-2 text-sm font-semibold">Ingredients</h4>
        <div className="rounded border">
          <table className="w-full text-sm">
            <tbody>
              {order.scaled_ingredients.map((ing, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="px-3 py-1.5">{ing.name}</td>
                  <td className="px-3 py-1.5 text-right">{ing.amount}</td>
                  <td className="px-3 py-1.5 text-muted-foreground">{ing.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Steps */}
      <div>
        <h4 className="mb-2 text-sm font-semibold">Steps</h4>
        <ol className="space-y-2">
          {order.steps.map((step) => (
            <li key={step.order} className="flex gap-2 text-sm">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs">
                {step.order}
              </span>
              <div className="flex-1">
                <span>{step.description}</span>
                {step.ccp && (
                  <span className="ml-2 rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
                    CCP
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      {order.seasoning_notes && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <h5 className="text-xs font-medium text-amber-800">Seasoning Notes</h5>
          <p className="mt-1 text-xs text-amber-700">{order.seasoning_notes}</p>
        </div>
      )}

      {/* Status actions */}
      {onStatusChange && order.status !== "completed" && (
        <div className="flex gap-2">
          {order.status === "pending" && (
            <button
              onClick={() => onStatusChange("in_progress")}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              Start
            </button>
          )}
          {order.status === "in_progress" && (
            <button
              onClick={() => onStatusChange("completed")}
              className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
            >
              Complete
            </button>
          )}
        </div>
      )}
    </div>
  );
}
