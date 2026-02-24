"use client";

import type { Inventory } from "@/types";

interface InventoryGridProps {
  items: Inventory[];
  isLoading?: boolean;
}

export function InventoryGrid({ items, isLoading }: InventoryGridProps) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        재고 데이터 로딩 중...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        재고 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">품목명</th>
            <th className="px-4 py-3 text-left font-medium">카테고리</th>
            <th className="px-4 py-3 text-right font-medium">현재고</th>
            <th className="px-4 py-3 text-right font-medium">최소재고</th>
            <th className="px-4 py-3 text-left font-medium">보관위치</th>
            <th className="px-4 py-3 text-left font-medium">최종갱신</th>
            <th className="px-4 py-3 text-center font-medium">상태</th>
          </tr>
        </thead>
        <tbody>
          {items.map((inv) => (
            <tr
              key={inv.id}
              className={`border-b last:border-0 hover:bg-muted/30 ${inv.is_low_stock ? "bg-red-50/50" : ""}`}
            >
              <td className="px-4 py-2.5 font-medium">{inv.item_name ?? inv.item_id}</td>
              <td className="px-4 py-2.5 text-muted-foreground">{inv.item_category ?? "-"}</td>
              <td className="px-4 py-2.5 text-right font-semibold">
                {inv.quantity.toLocaleString()} {inv.unit}
              </td>
              <td className="px-4 py-2.5 text-right text-muted-foreground">
                {inv.min_qty ? `${inv.min_qty.toLocaleString()} ${inv.unit}` : "-"}
              </td>
              <td className="px-4 py-2.5 text-muted-foreground">{inv.location ?? "-"}</td>
              <td className="px-4 py-2.5 text-muted-foreground text-xs">
                {new Date(inv.last_updated).toLocaleDateString("ko-KR")}
              </td>
              <td className="px-4 py-2.5 text-center">
                {inv.is_low_stock ? (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
                    부족
                  </span>
                ) : (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                    정상
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
