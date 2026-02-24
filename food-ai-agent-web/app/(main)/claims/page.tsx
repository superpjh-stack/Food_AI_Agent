"use client";

import { useState } from "react";
import { useClaimsList } from "@/lib/hooks/use-claims";
import { useSiteStore } from "@/lib/stores/site-store";
import { ClaimListTable } from "@/components/claims/claim-list-table";
import { ClaimRegisterForm } from "@/components/claims/claim-register-form";
import { QualityReportViewer } from "@/components/claims/quality-report-viewer";

const STATUS_FILTERS = [
  { value: "", label: "전체" },
  { value: "open", label: "미처리" },
  { value: "investigating", label: "조사 중" },
  { value: "action_taken", label: "조치 완료" },
  { value: "closed", label: "종결" },
];

export default function ClaimsPage() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const [showForm, setShowForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const now = new Date();
  const { data, isLoading } = useClaimsList({
    status: statusFilter || undefined,
    page,
    perPage: 20,
  });

  const claims = data?.data ?? [];
  const meta = data?.meta ?? { total: 0, page: 1, per_page: 20 };
  const totalPages = Math.ceil(meta.total / meta.per_page);

  // Stats
  const open = claims.filter((c) => c.status === "open").length;
  const critical = claims.filter((c) => c.severity === "critical" && c.status !== "closed").length;
  const recurring = claims.filter((c) => c.is_recurring).length;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">클레임 관리</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
        >
          {showForm ? "닫기" : "클레임 접수"}
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border bg-card p-3 text-center">
          <div className="text-xl font-bold">{meta.total}</div>
          <div className="text-xs text-muted-foreground">전체 클레임</div>
        </div>
        <div className="rounded-lg border bg-card p-3 text-center">
          <div className={`text-xl font-bold ${open > 0 ? "text-orange-600" : "text-green-600"}`}>{open}</div>
          <div className="text-xs text-muted-foreground">미처리</div>
        </div>
        <div className="rounded-lg border bg-card p-3 text-center">
          <div className={`text-xl font-bold ${critical > 0 ? "text-red-600" : ""}`}>{critical}</div>
          <div className="text-xs text-muted-foreground">긴급</div>
        </div>
        <div className="rounded-lg border bg-card p-3 text-center">
          <div className={`text-xl font-bold ${recurring > 0 ? "text-yellow-600" : ""}`}>{recurring}</div>
          <div className="text-xs text-muted-foreground">재발</div>
        </div>
      </div>

      {showForm && (
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 font-semibold text-sm">새 클레임 접수</h2>
          <ClaimRegisterForm onSuccess={() => setShowForm(false)} />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setStatusFilter(f.value); setPage(1); }}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="animate-pulse h-32 rounded-lg bg-muted" />
      ) : (
        <ClaimListTable claims={claims} />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 text-sm">
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            이전
          </button>
          <span>{page} / {totalPages}</span>
          <button
            disabled={page === totalPages}
            onClick={() => setPage(page + 1)}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            다음
          </button>
        </div>
      )}

      <div className="rounded-lg border bg-card p-4">
        <h2 className="mb-3 font-semibold text-sm">
          {now.getFullYear()}년 {now.getMonth() + 1}월 품질 리포트
        </h2>
        <QualityReportViewer month={now.getMonth() + 1} year={now.getFullYear()} />
      </div>
    </div>
  );
}
