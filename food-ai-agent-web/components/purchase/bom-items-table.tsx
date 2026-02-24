"use client";

import type { BomItem } from "@/types";

interface BomItemsTableProps {
  items: BomItem[];
  isLoading?: boolean;
}

export function BomItemsTable({ items, isLoading }: BomItemsTableProps) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        로딩 중...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        BOM 항목이 없습니다.
      </div>
    );
  }

  const totalSubtotal = items.reduce((sum, bi) => sum + (bi.subtotal ?? 0), 0);

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-3 py-2.5 text-left font-medium">품목명</th>
            <th className="px-3 py-2.5 text-right font-medium">소요량</th>
            <th className="px-3 py-2.5 text-right font-medium">재고가용</th>
            <th className="px-3 py-2.5 text-right font-medium">발주필요</th>
            <th className="px-3 py-2.5 text-right font-medium">단가</th>
            <th className="px-3 py-2.5 text-right font-medium">예상금액</th>
          </tr>
        </thead>
        <tbody>
          {items.map((bi) => (
            <tr
              key={bi.id}
              className={`border-b last:border-0 hover:bg-muted/30 ${bi.order_quantity > 0 ? "" : "opacity-50"}`}
            >
              <td className="px-3 py-2">
                <span className="font-medium">{bi.item_name}</span>
                {bi.source_recipes.length > 0 && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    레시피 {bi.source_recipes.length}개
                  </p>
                )}
              </td>
              <td className="px-3 py-2 text-right">
                {bi.quantity.toLocaleString()} {bi.unit}
              </td>
              <td className="px-3 py-2 text-right text-green-600">
                {bi.inventory_available.toLocaleString()} {bi.unit}
              </td>
              <td className="px-3 py-2 text-right font-medium text-amber-600">
                {bi.order_quantity > 0
                  ? `${bi.order_quantity.toLocaleString()} ${bi.unit}`
                  : "-"}
              </td>
              <td className="px-3 py-2 text-right text-muted-foreground">
                {bi.unit_price ? `${bi.unit_price.toLocaleString()}원` : "-"}
              </td>
              <td className="px-3 py-2 text-right font-medium">
                {bi.subtotal ? `${bi.subtotal.toLocaleString()}원` : "-"}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t bg-muted/30">
            <td colSpan={5} className="px-3 py-2 font-medium text-right">
              합계
            </td>
            <td className="px-3 py-2 text-right font-bold text-primary">
              {totalSubtotal.toLocaleString()}원
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
