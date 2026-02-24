"use client";

import { useState } from "react";
import { useForecastList, useActualList, useSiteEvents } from "@/lib/hooks/use-forecast";
import { useSiteStore } from "@/lib/stores/site-store";
import { ForecastChart } from "@/components/forecast/forecast-chart";
import { HeadcountInputForm } from "@/components/forecast/headcount-input-form";
import { EventCalendarWidget } from "@/components/forecast/event-calendar-widget";
import { ForecastConfidenceBadge } from "@/components/forecast/forecast-confidence-badge";

export default function ForecastPage() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const today = new Date().toISOString().slice(0, 10);
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  const { data: forecastData, isLoading: forecastLoading } = useForecastList({
    dateFrom: thirtyDaysAgo,
    dateTo: today,
    mealType: "lunch",
  });

  const { data: actualData } = useActualList({
    dateFrom: thirtyDaysAgo,
    dateTo: today,
  });

  const { data: events } = useSiteEvents({
    dateFrom: today,
    dateTo: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  });

  // Merge forecast + actual data for chart
  const chartData = (() => {
    const forecastMap: Record<string, { predicted_mid?: number; predicted_min?: number; predicted_max?: number }> = {};
    const actualMap: Record<string, number> = {};

    if (forecastData && "data" in forecastData) {
      for (const f of (forecastData as { data: Array<{ forecast_date: string; predicted_mid: number; predicted_min: number; predicted_max: number }> }).data) {
        forecastMap[f.forecast_date] = {
          predicted_mid: f.predicted_mid,
          predicted_min: f.predicted_min,
          predicted_max: f.predicted_max,
        };
      }
    }
    if (actualData && "data" in actualData) {
      for (const a of (actualData as { data: Array<{ record_date: string; actual: number }> }).data) {
        actualMap[a.record_date] = a.actual;
      }
    }

    const allDates = new Set([...Object.keys(forecastMap), ...Object.keys(actualMap)]);
    return Array.from(allDates)
      .sort()
      .map((date) => ({
        date,
        ...forecastMap[date],
        actual: actualMap[date],
      }));
  })();

  const latestForecasts = forecastData && "data" in forecastData
    ? (forecastData as { data: Array<{ id: string; forecast_date: string; predicted_mid: number; confidence_pct: number }> }).data.slice(-5)
    : [];

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">수요 예측</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-sm">예측 vs 실제 (최근 30일)</h2>
            </div>
            {forecastLoading ? (
              <div className="h-64 animate-pulse rounded bg-muted" />
            ) : (
              <ForecastChart data={chartData} />
            )}
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h2 className="mb-3 font-semibold text-sm">최근 예측 신뢰도</h2>
            <div className="flex flex-wrap gap-2">
              {latestForecasts.map((f) => (
                <div key={f.id} className="flex items-center gap-2 text-xs">
                  <span>{f.forecast_date}</span>
                  <ForecastConfidenceBadge confidencePct={f.confidence_pct} />
                  <span className="text-muted-foreground">{f.predicted_mid}명</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <HeadcountInputForm />
          <EventCalendarWidget events={(events as SiteEvent[]) ?? []} />
        </div>
      </div>
    </div>
  );
}

// Local type for events
interface SiteEvent {
  id: string;
  site_id: string;
  event_date: string;
  event_type: string;
  event_name: string | null;
  adjustment_factor: number;
  affects_meal_types: string[];
  notes: string | null;
  created_at: string;
}
