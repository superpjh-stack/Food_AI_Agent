"use client";

interface NutritionData {
  date: string;
  kcal: number;
  protein: number;
  sodium: number;
}

interface NutritionChartProps {
  data: NutritionData[];
  criteria?: {
    kcal?: { min?: number; max?: number };
    protein?: { min?: number };
    sodium?: { max?: number };
  };
}

export function NutritionChart({ data, criteria }: NutritionChartProps) {
  if (!data.length) {
    return <div className="text-sm text-muted-foreground">No nutrition data available.</div>;
  }

  const maxKcal = Math.max(...data.map((d) => d.kcal), criteria?.kcal?.max ?? 0);
  const maxSodium = Math.max(...data.map((d) => d.sodium), criteria?.sodium?.max ?? 0);

  return (
    <div className="space-y-4">
      {/* Calorie bars */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Calories (kcal)</h4>
        <div className="space-y-1">
          {data.map((d) => {
            const pct = maxKcal > 0 ? (d.kcal / maxKcal) * 100 : 0;
            const overMax = criteria?.kcal?.max && d.kcal > criteria.kcal.max;
            const underMin = criteria?.kcal?.min && d.kcal < criteria.kcal.min;
            return (
              <div key={d.date} className="flex items-center gap-2">
                <span className="w-12 text-xs text-muted-foreground">{d.date.slice(5)}</span>
                <div className="relative h-5 flex-1 rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full ${
                      overMax || underMin ? "bg-red-400" : "bg-primary"
                    }`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                  {criteria?.kcal?.max && (
                    <div
                      className="absolute top-0 h-full w-0.5 bg-destructive"
                      style={{ left: `${(criteria.kcal.max / maxKcal) * 100}%` }}
                    />
                  )}
                </div>
                <span className="w-14 text-right text-xs">{d.kcal.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sodium bars */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Sodium (mg)</h4>
        <div className="space-y-1">
          {data.map((d) => {
            const pct = maxSodium > 0 ? (d.sodium / maxSodium) * 100 : 0;
            const over = criteria?.sodium?.max && d.sodium > criteria.sodium.max;
            return (
              <div key={d.date} className="flex items-center gap-2">
                <span className="w-12 text-xs text-muted-foreground">{d.date.slice(5)}</span>
                <div className="relative h-5 flex-1 rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full ${over ? "bg-red-400" : "bg-blue-400"}`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                  {criteria?.sodium?.max && (
                    <div
                      className="absolute top-0 h-full w-0.5 bg-destructive"
                      style={{ left: `${(criteria.sodium.max / maxSodium) * 100}%` }}
                    />
                  )}
                </div>
                <span className="w-14 text-right text-xs">{d.sodium.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
