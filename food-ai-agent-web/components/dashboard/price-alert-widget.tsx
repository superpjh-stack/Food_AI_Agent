"use client";

import Link from "next/link";

interface PriceAlert {
  item_id: string;
  item_name: string;
  vendor_name: string;
  change_pct: number;
  current_price: number;
  previous_price: number;
  unit: string;
}

interface PriceAlertWidgetProps {
  alerts: PriceAlert[];
  isLoading?: boolean;
}

export function PriceAlertWidget({ alerts, isLoading }: PriceAlertWidgetProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">단가 이상 알림</h3>
        <div className="mt-3 flex h-20 items-center justify-center text-xs text-muted-foreground">
          로딩 중...
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">단가 이상 알림</h3>
        <Link href="/purchase" className="text-xs text-primary hover:underline">
          발주 관리
        </Link>
      </div>

      {alerts.length === 0 ? (
        <div className="mt-3 flex h-16 items-center justify-center text-xs text-muted-foreground">
          이상 단가 없음
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          {alerts.slice(0, 4).map((alert) => (
            <div
              key={alert.item_id}
              className="flex items-center justify-between rounded-md border border-amber-200 bg-amber-50 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-xs font-medium">{alert.item_name}</p>
                <p className="truncate text-xs text-muted-foreground">{alert.vendor_name}</p>
              </div>
              <div className="ml-2 shrink-0 text-right">
                <span
                  className={`text-sm font-bold ${
                    alert.change_pct > 0 ? "text-red-600" : "text-green-600"
                  }`}
                >
                  {alert.change_pct > 0 ? "+" : ""}
                  {alert.change_pct.toFixed(1)}%
                </span>
                <p className="text-xs text-muted-foreground">
                  {alert.current_price.toLocaleString()}원/{alert.unit}
                </p>
              </div>
            </div>
          ))}
          {alerts.length > 4 && (
            <p className="text-right text-xs text-muted-foreground">
              외 {alerts.length - 4}건 더 보기
            </p>
          )}
        </div>
      )}
    </div>
  );
}
