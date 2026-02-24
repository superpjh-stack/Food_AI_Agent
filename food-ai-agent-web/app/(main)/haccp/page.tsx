"use client";

import Link from "next/link";
import { useCompletionStatus } from "@/lib/hooks/use-haccp";
import { useIncidents } from "@/lib/hooks/use-haccp";
import { HaccpStatusCard } from "@/components/haccp/haccp-status-card";

export default function HaccpPage() {
  const { data: completion, isLoading } = useCompletionStatus();
  const { data: incidentData } = useIncidents({ status: "open" });
  const openIncidents = (incidentData as unknown as { data: unknown[] })?.data ?? [];

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        Loading HACCP status...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">HACCP Management</h1>
        <p className="text-sm text-muted-foreground">
          Today's hygiene and food safety compliance overview
        </p>
      </div>

      {/* Status cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <HaccpStatusCard
          title="Completed"
          value={completion?.completed ?? 0}
          total={completion?.total ?? 0}
          status="success"
          subtitle="checklists done today"
        />
        <HaccpStatusCard
          title="In Progress"
          value={completion?.in_progress ?? 0}
          status="neutral"
          subtitle="currently being filled"
        />
        <HaccpStatusCard
          title="Pending"
          value={completion?.pending ?? 0}
          status={completion?.pending ? "warning" : "neutral"}
          subtitle="not yet started"
        />
        <HaccpStatusCard
          title="Open Incidents"
          value={openIncidents.length}
          status={openIncidents.length > 0 ? "danger" : "success"}
          subtitle="require attention"
        />
      </div>

      {/* Completion rate */}
      {completion && completion.total > 0 && (
        <div className="rounded-lg border p-4">
          <div className="flex items-center justify-between text-sm">
            <span>Today's Completion Rate</span>
            <span className="font-bold text-lg">{completion.completion_rate}%</span>
          </div>
          <div className="mt-2 h-3 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-green-500 transition-all"
              style={{ width: `${completion.completion_rate}%` }}
            />
          </div>
        </div>
      )}

      {/* Quick navigation */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <QuickLink href="/haccp/checklists" title="Checklists" description="View and manage inspection checklists" />
        <QuickLink href="/haccp/checklists" title="CCP Records" description="Temperature and time measurements" />
        <QuickLink href="/haccp/incidents" title="Incidents" description="Report and manage food safety incidents" />
        <QuickLink href="/haccp/reports" title="Audit Reports" description="Generate compliance reports" />
      </div>
    </div>
  );
}

function QuickLink({ href, title, description }: { href: string; title: string; description: string }) {
  return (
    <Link
      href={href}
      className="rounded-lg border p-4 transition-colors hover:bg-muted/30"
    >
      <h3 className="font-medium">{title}</h3>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </Link>
  );
}
