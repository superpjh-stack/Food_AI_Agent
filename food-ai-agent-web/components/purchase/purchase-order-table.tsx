"use client";

import Link from "next/link";
import type { PurchaseOrder } from "@/types";
import { POStatusBadge } from "./po-status-badge";

interface PurchaseOrderTableProps {
  orders: PurchaseOrder[];
  isLoading?: boolean;
}

export function PurchaseOrderTable({ orders, isLoading }: PurchaseOrderTableProps) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        로딩 중...
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
        발주서가 없습니다.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">발주번호</th>
            <th className="px-4 py-3 text-left font-medium">발주일</th>
            <th className="px-4 py-3 text-left font-medium">납품예정일</th>
            <th className="px-4 py-3 text-right font-medium">금액</th>
            <th className="px-4 py-3 text-left font-medium">상태</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((po) => (
            <tr key={po.id} className="border-b last:border-0 hover:bg-muted/30">
              <td className="px-4 py-3">
                <Link
                  href={`/purchase/${po.id}`}
                  className="font-medium text-primary hover:underline"
                >
                  {po.po_number ?? po.id.slice(0, 8)}
                </Link>
              </td>
              <td className="px-4 py-3 text-muted-foreground">{po.order_date}</td>
              <td className="px-4 py-3 text-muted-foreground">{po.delivery_date}</td>
              <td className="px-4 py-3 text-right font-medium">
                {po.total_amount.toLocaleString()}원
              </td>
              <td className="px-4 py-3">
                <POStatusBadge status={po.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
