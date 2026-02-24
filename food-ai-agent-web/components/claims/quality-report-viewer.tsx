"use client";

import { useQualityReport } from "@/lib/hooks/use-claims";
import { useSiteStore } from "@/lib/stores/site-store";

interface QualityReportViewerProps {
  month: number;
  year: number;
}

export function QualityReportViewer({ month, year }: QualityReportViewerProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { data, isLoading } = useQualityReport(siteId, month, year);

  if (isLoading) {
    return <div className="animate-pulse h-32 rounded-lg bg-muted" />;
  }
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="총 클레임" value={String(data.total_claims)} />
        <StatCard label="미처리" value={String(data.by_status.open ?? 0)} colorClass="text-red-600" />
        <StatCard label="재발" value={String(data.recurring_claims)} colorClass="text-orange-600" />
        <StatCard
          label="평균 해결일"
          value={data.avg_resolution_days != null ? `${data.avg_resolution_days}일` : "N/A"}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border p-3">
          <div className="mb-2 text-xs font-semibold">카테고리별</div>
          {Object.entries(data.by_category).map(([cat, cnt]) => (
            <div key={cat} className="flex justify-between text-xs py-0.5">
              <span className="text-muted-foreground">{cat}</span>
              <span className="font-medium">{cnt}건</span>
            </div>
          ))}
        </div>
        <div className="rounded-lg border p-3">
          <div className="mb-2 text-xs font-semibold">심각도별</div>
          {Object.entries(data.by_severity).map(([sev, cnt]) => (
            <div key={sev} className="flex justify-between text-xs py-0.5">
              <span className="text-muted-foreground">{sev}</span>
              <span className="font-medium">{cnt}건</span>
            </div>
          ))}
        </div>
      </div>

      {data.open_critical > 0 && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          긴급(Critical) 미처리 클레임 {data.open_critical}건 — 즉각 조치 필요
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  colorClass = "text-foreground",
}: {
  label: string;
  value: string;
  colorClass?: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-3 text-center">
      <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}
