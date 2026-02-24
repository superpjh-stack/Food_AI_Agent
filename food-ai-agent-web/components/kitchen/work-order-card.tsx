"use client";

import { cn } from "@/lib/utils/cn";
import type { WorkOrder } from "@/types";

interface WorkOrderCardProps {
  order: WorkOrder;
  onSelect: (order: WorkOrder) => void;
  isSelected: boolean;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: "Pending", color: "border-gray-200", bg: "bg-gray-50" },
  in_progress: { label: "In Progress", color: "border-blue-300", bg: "bg-blue-50" },
  completed: { label: "Done", color: "border-green-300", bg: "bg-green-50" },
};

export function WorkOrderCard({ order, onSelect, isSelected }: WorkOrderCardProps) {
  const status = STATUS_CONFIG[order.status] ?? STATUS_CONFIG.pending;

  return (
    <button
      onClick={() => onSelect(order)}
      className={cn(
        "w-full rounded-lg border-2 p-3 text-left transition-colors",
        status.color,
        isSelected ? "ring-2 ring-primary" : "hover:bg-muted/30",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">{order.recipe_name}</span>
        <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", status.bg)}>
          {status.label}
        </span>
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        {order.meal_type} / {order.scaled_servings} servings
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        {order.scaled_ingredients.length} ingredients / {order.steps.length} steps
      </div>
    </button>
  );
}
