"use client";

import type { SiteEvent } from "@/lib/hooks/use-forecast";

interface EventCalendarWidgetProps {
  events: SiteEvent[];
}

export function EventCalendarWidget({ events }: EventCalendarWidgetProps) {
  if (!events.length) {
    return (
      <div className="rounded-lg border bg-card p-4 text-center text-sm text-muted-foreground">
        예정된 이벤트가 없습니다.
      </div>
    );
  }

  const sorted = [...events].sort((a, b) =>
    a.event_date.localeCompare(b.event_date)
  );

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="mb-3 font-semibold text-sm">현장 이벤트</h3>
      <ul className="space-y-2">
        {sorted.map((ev) => {
          const factor = ev.adjustment_factor;
          const colorClass =
            factor >= 1.0
              ? "bg-blue-50 border-blue-200 text-blue-800"
              : factor >= 0.7
              ? "bg-yellow-50 border-yellow-200 text-yellow-800"
              : "bg-red-50 border-red-200 text-red-800";

          return (
            <li
              key={ev.id}
              className={`flex items-center justify-between rounded border px-3 py-2 text-xs ${colorClass}`}
            >
              <div>
                <span className="font-medium">{ev.event_date}</span>
                {ev.event_name && <span className="ml-2">{ev.event_name}</span>}
                <span className="ml-2 text-xs opacity-70">({ev.event_type})</span>
              </div>
              <span className="font-semibold">x{factor.toFixed(1)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
