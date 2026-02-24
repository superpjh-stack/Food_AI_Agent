"use client";

interface WeeklyStatusProps {
  menuConfirmed: number;
  menuTotal: number;
  confirmationRate: number;
}

export function WeeklyStatus({ menuConfirmed, menuTotal, confirmationRate }: WeeklyStatusProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="mb-3 text-sm font-semibold">This Week</h3>
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Menu Confirmation</span>
            <span className="font-medium">{menuConfirmed}/{menuTotal}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-green-500"
              style={{ width: `${confirmationRate}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{confirmationRate}% confirmed</p>
        </div>
      </div>
    </div>
  );
}
