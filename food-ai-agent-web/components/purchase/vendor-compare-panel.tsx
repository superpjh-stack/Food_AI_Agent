"use client";

interface VendorComparison {
  item_id: string;
  item_name: string;
  vendors: Array<{
    vendor_id: string;
    name: string;
    unit_price: number;
    unit: string;
    lead_days: number;
    rating: number;
    price_trend: string;
    recommended: boolean;
  }>;
}

interface VendorComparePanelProps {
  comparisons: VendorComparison[];
  totalSavings?: number;
  isLoading?: boolean;
}

export function VendorComparePanel({
  comparisons,
  totalSavings,
  isLoading,
}: VendorComparePanelProps) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        벤더 비교 데이터 로딩 중...
      </div>
    );
  }

  if (comparisons.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-muted-foreground text-sm">
        비교할 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {totalSavings !== undefined && totalSavings > 0 && (
        <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
          최적화 시 예상 절감액: <strong>{totalSavings.toLocaleString()}원</strong>
        </div>
      )}

      {comparisons.map((comp) => (
        <div key={comp.item_id} className="rounded-lg border p-4">
          <h4 className="mb-3 font-medium">{comp.item_name}</h4>
          <div className="space-y-2">
            {comp.vendors.map((v) => (
              <div
                key={v.vendor_id}
                className={`flex items-center justify-between rounded-md px-3 py-2 text-sm ${
                  v.recommended ? "bg-green-50 border border-green-200" : "bg-muted/30"
                }`}
              >
                <div className="flex items-center gap-2">
                  {v.recommended && (
                    <span className="rounded-full bg-green-600 px-1.5 py-0.5 text-xs text-white">
                      추천
                    </span>
                  )}
                  <span className="font-medium">{v.name}</span>
                </div>
                <div className="flex items-center gap-4 text-muted-foreground">
                  <span className="font-semibold text-foreground">
                    {v.unit_price.toLocaleString()}원/{v.unit}
                  </span>
                  <span className={v.price_trend.startsWith("+") ? "text-red-600" : "text-green-600"}>
                    {v.price_trend}
                  </span>
                  <span>납기 {v.lead_days}일</span>
                  <span>평점 {v.rating.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
