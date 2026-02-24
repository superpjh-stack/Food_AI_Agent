"use client";

interface ForecastStatusWidgetProps {
  forecastData?: {
    forecast_date: string;
    predicted_mid: number;
    predicted_min: number;
    predicted_max: number;
    confidence_pct: number | null;
  };
}

export function ForecastStatusWidget({ forecastData }: ForecastStatusWidgetProps) {
  if (!forecastData || !forecastData.predicted_mid) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <div className="text-xs text-muted-foreground">수요 예측</div>
        <div className="mt-1 text-sm text-muted-foreground">예측 데이터 없음</div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-xs text-muted-foreground">오늘 예측 식수</div>
      <div className="mt-1 text-2xl font-bold text-indigo-600">
        {forecastData.predicted_mid.toLocaleString()}명
      </div>
      <div className="text-xs text-muted-foreground">
        범위: {forecastData.predicted_min} ~ {forecastData.predicted_max}
      </div>
      {forecastData.confidence_pct != null && (
        <div className="text-xs text-muted-foreground">
          신뢰도: {forecastData.confidence_pct.toFixed(1)}%
        </div>
      )}
    </div>
  );
}
