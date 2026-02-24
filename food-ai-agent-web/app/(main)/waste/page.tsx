"use client";

import { useWasteRecords, useWasteSummary, useMenuPreferences } from "@/lib/hooks/use-waste";
import { WasteInputForm } from "@/components/waste/waste-input-form";
import { WasteTrendChart } from "@/components/waste/waste-trend-chart";
import { WasteByMenuTable } from "@/components/waste/waste-by-menu-table";
import { MenuPreferenceRating } from "@/components/waste/menu-preference-rating";

export default function WastePage() {
  const { data: summaryData } = useWasteSummary(30);
  const { data: prefData } = useMenuPreferences();

  // Build trend data: group waste records by date
  const { data: recordsData } = useWasteRecords({
    dateFrom: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  });

  const trendData = (() => {
    if (!recordsData || !("data" in recordsData)) return [];
    const byDate: Record<string, { sum: number; count: number }> = {};
    for (const r of (recordsData as { data: Array<{ record_date: string; waste_pct: number | null }> }).data) {
      if (r.waste_pct == null) continue;
      if (!byDate[r.record_date]) byDate[r.record_date] = { sum: 0, count: 0 };
      byDate[r.record_date].sum += r.waste_pct;
      byDate[r.record_date].count += 1;
    }
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, { sum, count }]) => ({
        date,
        avg_waste_pct: Math.round((sum / count) * 10) / 10,
      }));
  })();

  const summaryItems = summaryData?.items ?? [];
  const preferences = prefData && "data" in prefData
    ? (prefData as { data: typeof preferences }).data
    : [];

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-xl font-bold">잔반 관리</h1>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h2 className="mb-3 font-semibold text-sm">잔반률 추이 (30일)</h2>
            <WasteTrendChart data={trendData} targetPct={10} />
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h2 className="mb-3 font-semibold text-sm">메뉴별 잔반률 (높은 순)</h2>
            <WasteByMenuTable items={summaryItems} />
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h2 className="mb-3 font-semibold text-sm">메뉴 선호도</h2>
            <MenuPreferenceRating preferences={preferences} />
          </div>
        </div>

        <div>
          <WasteInputForm />
        </div>
      </div>
    </div>
  );
}
