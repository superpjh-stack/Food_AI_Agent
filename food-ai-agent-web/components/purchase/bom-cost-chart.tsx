"use client";

interface CostBreakdown {
  category: string;
  amount: number;
  percentage: number;
}

interface BomCostChartProps {
  totalCost: number;
  costPerMeal?: number;
  headcount: number;
  categoryBreakdown?: CostBreakdown[];
  isLoading?: boolean;
}

const CATEGORY_COLORS: Record<string, string> = {
  육류: "bg-red-400",
  수산: "bg-blue-400",
  채소: "bg-green-400",
  양념: "bg-amber-400",
  유제품: "bg-purple-400",
  기타: "bg-gray-400",
};

export function BomCostChart({
  totalCost,
  costPerMeal,
  headcount,
  categoryBreakdown = [],
  isLoading,
}: BomCostChartProps) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        원가 데이터 로딩 중...
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-5">
      <h3 className="mb-4 text-sm font-semibold">원가 구성</h3>

      <div className="mb-4 grid grid-cols-3 gap-3 text-center text-sm">
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">총 원가</p>
          <p className="mt-1 font-bold text-primary">{totalCost.toLocaleString()}원</p>
        </div>
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">식수</p>
          <p className="mt-1 font-bold">{headcount.toLocaleString()}명</p>
        </div>
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">식당 원가</p>
          <p className="mt-1 font-bold">
            {costPerMeal ? `${costPerMeal.toLocaleString()}원` : "-"}
          </p>
        </div>
      </div>

      {categoryBreakdown.length > 0 && (
        <div className="space-y-2">
          {categoryBreakdown.map((cat) => (
            <div key={cat.category}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-medium">{cat.category}</span>
                <span className="text-muted-foreground">
                  {cat.amount.toLocaleString()}원 ({cat.percentage}%)
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full rounded-full ${CATEGORY_COLORS[cat.category] ?? "bg-gray-400"}`}
                  style={{ width: `${cat.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
