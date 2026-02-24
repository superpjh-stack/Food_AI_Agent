"use client";

interface AuditReportData {
  period: { start: string; end: string };
  site_id: string;
  checklists: {
    total: number;
    completed: number;
    overdue: number;
    completion_rate: number;
  };
  ccp_records: {
    total: number;
    compliant: number;
    noncompliant: number;
    compliance_rate: number;
  };
  incidents: {
    total: number;
    by_severity: Record<string, number>;
    resolved: number;
  };
}

interface AuditReportProps {
  data: AuditReportData;
}

export function AuditReport({ data }: AuditReportProps) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 print:space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between print:block">
        <div>
          <h2 className="text-xl font-bold">HACCP Audit Report</h2>
          <p className="text-sm text-muted-foreground">
            Period: {data.period.start} ~ {data.period.end}
          </p>
        </div>
        <button
          onClick={handlePrint}
          className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted/50 print:hidden"
        >
          Print / Download
        </button>
      </div>

      {/* Checklist Section */}
      <section className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Checklist Compliance</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatBlock label="Total Checklists" value={data.checklists.total} />
          <StatBlock label="Completed" value={data.checklists.completed} />
          <StatBlock label="Overdue" value={data.checklists.overdue} highlight={data.checklists.overdue > 0} />
        </div>
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Completion Rate</span>
            <span className="font-medium">{data.checklists.completion_rate}%</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-green-500"
              style={{ width: `${data.checklists.completion_rate}%` }}
            />
          </div>
        </div>
      </section>

      {/* CCP Records Section */}
      <section className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">CCP Records</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatBlock label="Total Records" value={data.ccp_records.total} />
          <StatBlock label="Compliant" value={data.ccp_records.compliant} />
          <StatBlock label="Non-compliant" value={data.ccp_records.noncompliant} highlight={data.ccp_records.noncompliant > 0} />
        </div>
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Compliance Rate</span>
            <span className="font-medium">{data.ccp_records.compliance_rate}%</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-blue-500"
              style={{ width: `${data.ccp_records.compliance_rate}%` }}
            />
          </div>
        </div>
      </section>

      {/* Incidents Section */}
      <section className="rounded-lg border p-4">
        <h3 className="mb-3 text-sm font-semibold">Incidents</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatBlock label="Total Incidents" value={data.incidents.total} />
          <StatBlock label="Resolved" value={data.incidents.resolved} />
          <StatBlock
            label="Unresolved"
            value={data.incidents.total - data.incidents.resolved}
            highlight={data.incidents.total - data.incidents.resolved > 0}
          />
        </div>
        {Object.keys(data.incidents.by_severity).length > 0 && (
          <div className="mt-3 flex gap-2">
            {Object.entries(data.incidents.by_severity).map(([sev, count]) => (
              <span
                key={sev}
                className="rounded-full border px-2 py-0.5 text-xs"
              >
                {sev}: {count}
              </span>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatBlock({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="text-center">
      <div className={`text-2xl font-bold ${highlight ? "text-red-600" : ""}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}
