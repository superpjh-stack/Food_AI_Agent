"use client";

import { useParams } from "next/navigation";
import { useMenuPlan, useValidateMenuPlan, useConfirmMenuPlan } from "@/lib/hooks/use-menu-plans";
import { MenuCalendar } from "@/components/menu/menu-calendar";
import { NutritionChart } from "@/components/menu/nutrition-chart";
import { ValidationPanel } from "@/components/menu/validation-panel";
import { useState } from "react";

export default function MenuPlanDetailPage() {
  const params = useParams();
  const planId = params.id as string;
  const { data: plan, isLoading } = useMenuPlan(planId);
  const validateMutation = useValidateMenuPlan();
  const confirmMutation = useConfirmMenuPlan();
  const [validationResult, setValidationResult] = useState<{
    overall_status: "pass" | "warning" | "fail";
    daily_results: Record<string, { totals: Record<string, number>; status: "pass" | "warning" | "fail"; violations: string[] }>;
  } | null>(null);

  if (isLoading) {
    return (
      <div className="flex h-60 items-center justify-center text-muted-foreground">
        Loading menu plan...
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex h-60 items-center justify-center text-muted-foreground">
        Menu plan not found.
      </div>
    );
  }

  const handleValidate = async () => {
    try {
      const result = await validateMutation.mutateAsync(planId);
      setValidationResult(result as typeof validationResult);
    } catch {
      // handled by TanStack Query
    }
  };

  const handleConfirm = async () => {
    try {
      await confirmMutation.mutateAsync(planId);
    } catch {
      // handled by TanStack Query
    }
  };

  // Aggregate nutrition data for chart
  const nutritionByDate = new Map<string, { kcal: number; protein: number; sodium: number }>();
  for (const item of plan.items ?? []) {
    if (!item.nutrition) continue;
    const existing = nutritionByDate.get(item.date) ?? { kcal: 0, protein: 0, sodium: 0 };
    existing.kcal += item.nutrition.kcal ?? 0;
    existing.protein += item.nutrition.protein ?? 0;
    existing.sodium += item.nutrition.sodium ?? 0;
    nutritionByDate.set(item.date, existing);
  }
  const nutritionData = Array.from(nutritionByDate.entries())
    .map(([date, totals]) => ({ date, ...totals }))
    .sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{plan.title ?? "Untitled Menu Plan"}</h1>
          <p className="text-sm text-muted-foreground">
            {plan.period_start} ~ {plan.period_end} / {plan.target_headcount} headcount / v{plan.version}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleValidate}
            disabled={validateMutation.isPending}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted/50 disabled:opacity-50"
          >
            {validateMutation.isPending ? "Validating..." : "Validate"}
          </button>
          {plan.status === "review" && (
            <button
              onClick={handleConfirm}
              disabled={confirmMutation.isPending}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {confirmMutation.isPending ? "Confirming..." : "Confirm"}
            </button>
          )}
        </div>
      </div>

      {/* Calendar view */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Menu Calendar</h2>
        <MenuCalendar
          items={plan.items ?? []}
          periodStart={plan.period_start}
          periodEnd={plan.period_end}
        />
      </div>

      {/* Nutrition chart */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Nutrition Overview</h2>
        <NutritionChart data={nutritionData} />
      </div>

      {/* Validation panel */}
      {validationResult && (
        <ValidationPanel
          policyName="Site Nutrition Policy"
          overallStatus={validationResult.overall_status}
          dailyResults={validationResult.daily_results}
        />
      )}
    </div>
  );
}
