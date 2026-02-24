"use client";

import { useCostAnalyses, useCostTrend } from "@/lib/hooks/use-cost-analysis";
import { CostSimulationPanel } from "@/components/cost/cost-simulation-panel";
import { BudgetVsActualChart } from "@/components/cost/budget-vs-actual-chart";
import { CostVarianceIndicator } from "@/components/cost/cost-variance-indicator";
import { MenuSwapSuggestionCard } from "@/components/cost/menu-swap-suggestion-card";

export default function CostOptimizerPage() {
  const { data: analysesData } = useCostAnalyses();
  const { data: trendData } = useCostTrend(90);

  const analyses = analysesData && "data" in analysesData
    ? (analysesData as { data: Array<{
        id: string;
        variance_pct: number | null;
        alert_triggered: string | null;
        suggestions: Array<{ item_name: string; current_cost: number; suggestion: string }>;
        estimated_cost: number | null;
        target_cost: number | null;
        actual_cost: number | null;
        created_at: string;
      }> }).data
    : [];

  const chartData = (trendData?.trend ?? []).map((t) => ({
    label: t.date?.slice(5) ?? "",
    target: 0,
    estimated: t.estimated_cost ?? 0,
    actual: t.actual_cost ?? 0,
  }));

  const latestAnalysis = analyses[0];
  const allSuggestions = analyses.flatMap((a) => a.suggestions ?? []).slice(0, 5);

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-xl font-bold">원가 최적화</h1>

      <div className="grid gap-6 lg:grid-cols-3">
        <div>
          <CostSimulationPanel />
        </div>

        <div className="lg:col-span-2 space-y-4">
          {latestAnalysis && (
            <div className="rounded-lg border bg-card p-4">
              <h2 className="mb-3 font-semibold text-sm">최근 시뮬레이션 결과</h2>
              <CostVarianceIndicator
                variancePct={latestAnalysis.variance_pct ?? 0}
                alertTriggered={latestAnalysis.alert_triggered ?? "none"}
              />
            </div>
          )}

          <div className="rounded-lg border bg-card p-4">
            <h2 className="mb-3 font-semibold text-sm">원가 추이 (90일)</h2>
            <BudgetVsActualChart data={chartData} />
          </div>

          {allSuggestions.length > 0 && (
            <div className="rounded-lg border bg-card p-4">
              <h2 className="mb-3 font-semibold text-sm">AI 절감 제안</h2>
              <div className="space-y-2">
                {allSuggestions.map((s, i) => (
                  <MenuSwapSuggestionCard key={i} suggestion={s} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
