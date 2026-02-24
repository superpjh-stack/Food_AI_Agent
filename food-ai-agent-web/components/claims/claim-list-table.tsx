"use client";

import Link from "next/link";
import type { Claim } from "@/lib/hooks/use-claims";
import { ClaimCategoryBadge } from "./claim-category-badge";
import { ClaimSeverityIndicator } from "./claim-severity-indicator";

interface ClaimListTableProps {
  claims: Claim[];
}

const STATUS_LABELS: Record<string, string> = {
  open: "미처리",
  investigating: "조사 중",
  action_taken: "조치 완료",
  closed: "종결",
  recurred: "재발",
};

export function ClaimListTable({ claims }: ClaimListTableProps) {
  if (!claims.length) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        클레임이 없습니다.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-2 text-left font-medium">발생일</th>
            <th className="px-4 py-2 text-left font-medium">카테고리</th>
            <th className="px-4 py-2 text-left font-medium">심각도</th>
            <th className="px-4 py-2 text-left font-medium">제목</th>
            <th className="px-4 py-2 text-left font-medium">상태</th>
            <th className="px-4 py-2 text-left font-medium">재발</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody>
          {claims.map((c) => (
            <tr key={c.id} className="border-b last:border-0 hover:bg-muted/30">
              <td className="px-4 py-2 text-xs text-muted-foreground">
                {new Date(c.incident_date).toLocaleDateString("ko-KR")}
              </td>
              <td className="px-4 py-2">
                <ClaimCategoryBadge category={c.category} />
              </td>
              <td className="px-4 py-2">
                <ClaimSeverityIndicator severity={c.severity} />
              </td>
              <td className="px-4 py-2 max-w-xs truncate font-medium">{c.title}</td>
              <td className="px-4 py-2 text-xs">
                {STATUS_LABELS[c.status] ?? c.status}
              </td>
              <td className="px-4 py-2 text-center">
                {c.is_recurring && (
                  <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700">
                    재발 {c.recurrence_count}
                  </span>
                )}
              </td>
              <td className="px-4 py-2">
                <Link
                  href={`/claims/${c.id}`}
                  className="text-xs text-primary hover:underline"
                >
                  상세
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
