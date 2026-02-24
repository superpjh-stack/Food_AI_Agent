"use client";

import { useState } from "react";
import { useSimulateCost, type CostSimulateResult } from "@/lib/hooks/use-cost-analysis";
import { useSiteStore } from "@/lib/stores/site-store";
import { CostVarianceIndicator } from "./cost-variance-indicator";

export function CostSimulationPanel() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { mutate: simulate, isPending } = useSimulateCost();

  const [form, setForm] = useState({
    menu_plan_id: "",
    target_cost_per_meal: "",
    headcount: "",
  });
  const [result, setResult] = useState<CostSimulateResult | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteId) return;
    simulate(
      {
        site_id: siteId,
        menu_plan_id: form.menu_plan_id,
        target_cost_per_meal: Number(form.target_cost_per_meal),
        headcount: Number(form.headcount),
        suggest_alternatives: true,
      },
      { onSuccess: (data) => setResult(data) }
    );
  };

  return (
    <div className="rounded-lg border bg-card p-4 space-y-4">
      <h3 className="font-semibold text-sm">원가 시뮬레이션</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="text-xs text-muted-foreground">식단 ID</label>
          <input
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.menu_plan_id}
            onChange={(e) => setForm({ ...form, menu_plan_id: e.target.value })}
            placeholder="Menu Plan UUID"
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-muted-foreground">1인 목표 원가 (KRW)</label>
            <input
              type="number"
              className="w-full rounded border px-2 py-1 text-sm"
              value={form.target_cost_per_meal}
              onChange={(e) => setForm({ ...form, target_cost_per_meal: e.target.value })}
              placeholder="3500"
              required
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">식수</label>
            <input
              type="number"
              className="w-full rounded border px-2 py-1 text-sm"
              value={form.headcount}
              onChange={(e) => setForm({ ...form, headcount: e.target.value })}
              placeholder="300"
              required
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={isPending}
          className="w-full rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {isPending ? "계산 중..." : "원가 시뮬레이션"}
        </button>
      </form>

      {result && (
        <div className="space-y-3 border-t pt-3">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <div className="text-muted-foreground">예상 1인 원가</div>
              <div className="font-semibold text-base">
                {result.estimated_cost_per_meal.toLocaleString()}원
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">목표 1인 원가</div>
              <div className="font-semibold text-base">
                {result.target_cost_per_meal.toLocaleString()}원
              </div>
            </div>
          </div>
          <CostVarianceIndicator
            variancePct={result.variance_pct}
            alertTriggered={result.alert_triggered}
          />
          {result.suggestions.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-medium">AI 절감 제안</div>
              <ul className="space-y-1">
                {result.suggestions.map((s, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    • {s.suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
