"use client";

interface OverviewCardsProps {
  menuStatus: Record<string, number>;
  haccpCompletionRate: number;
  workOrderCompletionRate: number;
}

export function OverviewCards({ menuStatus, haccpCompletionRate, workOrderCompletionRate }: OverviewCardsProps) {
  const totalMenus = Object.values(menuStatus).reduce((a, b) => a + b, 0);
  const confirmed = menuStatus.confirmed ?? 0;

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <div className="rounded-lg border bg-card p-4">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">Menu Plans</h3>
        <div className="mt-2 text-2xl font-bold">{confirmed}/{totalMenus}</div>
        <p className="text-xs text-muted-foreground">confirmed this week</p>
        <div className="mt-2 flex gap-1">
          {menuStatus.draft > 0 && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
              {menuStatus.draft} draft
            </span>
          )}
          {menuStatus.review > 0 && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
              {menuStatus.review} review
            </span>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-card p-4">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">HACCP Compliance</h3>
        <div className="mt-2 text-2xl font-bold">{haccpCompletionRate}%</div>
        <p className="text-xs text-muted-foreground">today's checklist completion</p>
        <div className="mt-2 h-2 rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-green-500 transition-all"
            style={{ width: `${haccpCompletionRate}%` }}
          />
        </div>
      </div>

      <div className="rounded-lg border bg-card p-4">
        <h3 className="text-xs font-medium uppercase text-muted-foreground">Work Orders</h3>
        <div className="mt-2 text-2xl font-bold">{workOrderCompletionRate}%</div>
        <p className="text-xs text-muted-foreground">today's completion rate</p>
        <div className="mt-2 h-2 rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${workOrderCompletionRate}%` }}
          />
        </div>
      </div>
    </div>
  );
}
