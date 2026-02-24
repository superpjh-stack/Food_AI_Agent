"use client";

import { useState } from "react";
import { useSiteStore } from "@/lib/stores/site-store";
import { useAuditReport } from "@/lib/hooks/use-haccp";
import { AuditReport } from "@/components/haccp/audit-report";

export default function ReportsPage() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const reportMutation = useAuditReport();
  const [reportData, setReportData] = useState<Record<string, unknown> | null>(null);

  const handleGenerate = async () => {
    if (!siteId || !startDate || !endDate) return;
    const result = await reportMutation.mutateAsync({
      site_id: siteId,
      start_date: startDate,
      end_date: endDate,
    });
    setReportData(result);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit Reports</h1>
        <p className="text-sm text-muted-foreground">
          Generate HACCP compliance audit reports
        </p>
      </div>

      {/* Form */}
      <div className="flex flex-wrap items-end gap-4 rounded-lg border p-4">
        <div>
          <label className="block text-sm font-medium">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="mt-1 rounded-md border bg-background px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="mt-1 rounded-md border bg-background px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={handleGenerate}
          disabled={reportMutation.isPending || !startDate || !endDate}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {reportMutation.isPending ? "Generating..." : "Generate Report"}
        </button>
      </div>

      {/* Report */}
      {reportData && (
        <AuditReport
          data={reportData as {
            period: { start: string; end: string };
            site_id: string;
            checklists: { total: number; completed: number; overdue: number; completion_rate: number };
            ccp_records: { total: number; compliant: number; noncompliant: number; compliance_rate: number };
            incidents: { total: number; by_severity: Record<string, number>; resolved: number };
          }}
        />
      )}
    </div>
  );
}
