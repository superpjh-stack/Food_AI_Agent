"use client";

interface Activity {
  id: string;
  action: string;
  entity_type: string;
  reason: string | null;
  created_at: string | null;
}

interface ActivityFeedProps {
  activities: Activity[];
}

const ACTION_LABELS: Record<string, string> = {
  create: "Created",
  update: "Updated",
  confirm: "Confirmed",
  reject: "Rejected",
  delete: "Deleted",
};

const ENTITY_LABELS: Record<string, string> = {
  menu_plan: "Menu Plan",
  recipe: "Recipe",
  haccp_checklist: "HACCP Checklist",
  haccp_record: "CCP Record",
  haccp_incident: "Incident",
  work_order: "Work Order",
};

export function ActivityFeed({ activities }: ActivityFeedProps) {
  if (!activities.length) {
    return (
      <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        No recent activity.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="mb-3 text-sm font-semibold">Recent Activity</h3>
      <div className="space-y-3">
        {activities.map((a) => {
          const timeStr = a.created_at
            ? new Date(a.created_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })
            : "";
          return (
            <div key={a.id} className="flex items-start gap-3 text-sm">
              <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
              <div className="flex-1">
                <span className="font-medium">{ACTION_LABELS[a.action] ?? a.action}</span>
                {" "}
                <span className="text-muted-foreground">
                  {ENTITY_LABELS[a.entity_type] ?? a.entity_type}
                </span>
                {a.reason && (
                  <p className="mt-0.5 text-xs text-muted-foreground">{a.reason}</p>
                )}
              </div>
              <span className="shrink-0 text-xs text-muted-foreground">{timeStr}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
