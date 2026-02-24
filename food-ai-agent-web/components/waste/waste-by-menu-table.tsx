"use client";

import type { WasteSummaryItem } from "@/lib/hooks/use-waste";

interface WasteByMenuTableProps {
  items: WasteSummaryItem[];
}

export function WasteByMenuTable({ items }: WasteByMenuTableProps) {
  if (!items.length) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        잔반 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-2 text-left font-medium">메뉴명</th>
            <th className="px-4 py-2 text-right font-medium">평균 잔반률</th>
            <th className="px-4 py-2 text-right font-medium">기록 수</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => {
            const pct = item.avg_waste_pct;
            const colorClass =
              pct >= 30
                ? "text-red-600"
                : pct >= 15
                ? "text-yellow-600"
                : "text-green-600";

            return (
              <tr key={idx} className="border-b last:border-0 hover:bg-muted/30">
                <td className="px-4 py-2">{item.item_name}</td>
                <td className={`px-4 py-2 text-right font-semibold ${colorClass}`}>
                  {pct.toFixed(1)}%
                </td>
                <td className="px-4 py-2 text-right text-muted-foreground">
                  {item.total_records}건
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
