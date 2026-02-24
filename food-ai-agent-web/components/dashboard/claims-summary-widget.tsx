"use client";

import Link from "next/link";

interface ClaimsSummaryWidgetProps {
  claimsData?: {
    open_claims: number;
    critical_claims: number;
  };
}

export function ClaimsSummaryWidget({ claimsData }: ClaimsSummaryWidgetProps) {
  const open = claimsData?.open_claims ?? 0;
  const critical = claimsData?.critical_claims ?? 0;

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">미처리 클레임</div>
        <Link href="/claims" className="text-xs text-primary hover:underline">
          전체보기
        </Link>
      </div>
      <div className={`mt-1 text-2xl font-bold ${open > 0 ? "text-orange-600" : "text-green-600"}`}>
        {open}건
      </div>
      {critical > 0 && (
        <div className="mt-1 flex items-center gap-1 text-xs text-red-600">
          <span className="h-1.5 w-1.5 rounded-full bg-red-600" />
          긴급 {critical}건 즉각 조치 필요
        </div>
      )}
    </div>
  );
}
