"use client";

interface ExpiryAlert {
  lot_id: string;
  item_id: string;
  item_name?: string;
  lot_number?: string;
  quantity: number;
  unit: string;
  expiry_date: string;
  days_until_expiry: number;
}

interface ExpiryAlertListProps {
  critical: ExpiryAlert[];
  warning: ExpiryAlert[];
  isLoading?: boolean;
}

export function ExpiryAlertList({ critical, warning, isLoading }: ExpiryAlertListProps) {
  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center text-muted-foreground text-sm">
        유통기한 데이터 로딩 중...
      </div>
    );
  }

  if (critical.length === 0 && warning.length === 0) {
    return (
      <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
        유통기한 임박 품목이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {critical.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-red-700">
            D-3 이하 ({critical.length}건)
          </h4>
          <div className="space-y-2">
            {critical.map((item) => (
              <ExpiryItem key={item.lot_id} item={item} severity="critical" />
            ))}
          </div>
        </div>
      )}

      {warning.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-amber-700">
            D-4 ~ D-7 ({warning.length}건)
          </h4>
          <div className="space-y-2">
            {warning.map((item) => (
              <ExpiryItem key={item.lot_id} item={item} severity="warning" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ExpiryItem({
  item,
  severity,
}: {
  item: ExpiryAlert;
  severity: "critical" | "warning";
}) {
  const bgClass = severity === "critical" ? "bg-red-50 border-red-100" : "bg-amber-50 border-amber-100";
  const badgeClass = severity === "critical" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700";

  return (
    <div className={`flex items-center justify-between rounded-md border px-4 py-3 ${bgClass}`}>
      <div>
        <p className="text-sm font-medium">{item.item_name ?? item.item_id}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {item.lot_number && `로트: ${item.lot_number} · `}
          {item.quantity.toLocaleString()} {item.unit}
        </p>
      </div>
      <div className="text-right">
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${badgeClass}`}>
          D-{item.days_until_expiry}
        </span>
        <p className="mt-1 text-xs text-muted-foreground">{item.expiry_date}</p>
      </div>
    </div>
  );
}
