"use client";

import Link from "next/link";

interface PurchaseStatusWidgetProps {
  draft: number;
  submitted: number;
  approved: number;
  received: number;
  todayDeliveries: number;
}

export function PurchaseStatusWidget({
  draft,
  submitted,
  approved,
  received,
  todayDeliveries,
}: PurchaseStatusWidgetProps) {
  const total = draft + submitted + approved + received;

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">발주 현황</h3>
        <Link
          href="/purchase"
          className="text-xs text-primary hover:underline"
        >
          전체 보기
        </Link>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-md bg-muted/50 p-2 text-center">
          <p className="text-lg font-bold">{todayDeliveries}</p>
          <p className="text-xs text-muted-foreground">오늘 납품 예정</p>
        </div>
        <div className="rounded-md bg-muted/50 p-2 text-center">
          <p className="text-lg font-bold">{total}</p>
          <p className="text-xs text-muted-foreground">전체 발주서</p>
        </div>
      </div>

      <div className="mt-3 space-y-1.5">
        <StatusRow label="초안" count={draft} colorClass="bg-gray-400" />
        <StatusRow label="제출됨" count={submitted} colorClass="bg-blue-500" />
        <StatusRow label="승인됨" count={approved} colorClass="bg-green-500" />
        <StatusRow label="수령완료" count={received} colorClass="bg-slate-500" />
      </div>
    </div>
  );
}

function StatusRow({
  label,
  count,
  colorClass,
}: {
  label: string;
  count: number;
  colorClass: string;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <div className="flex items-center gap-1.5">
        <span className={`inline-block h-2 w-2 rounded-full ${colorClass}`} />
        <span className="text-muted-foreground">{label}</span>
      </div>
      <span className="font-medium">{count}건</span>
    </div>
  );
}
