"use client";

import type { ClaimAction } from "@/lib/hooks/use-claims";

interface ClaimActionTrackerProps {
  actions: ClaimAction[];
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-200 text-gray-700",
  in_progress: "bg-blue-200 text-blue-700",
  done: "bg-green-200 text-green-700",
};

export function ClaimActionTracker({ actions }: ClaimActionTrackerProps) {
  if (!actions.length) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        등록된 조치가 없습니다.
      </div>
    );
  }

  return (
    <div className="relative space-y-3 pl-4">
      {/* Vertical line */}
      <div className="absolute left-1.5 top-2 bottom-2 w-0.5 bg-border" />

      {actions.map((action) => (
        <div key={action.id} className="relative pl-4">
          {/* Timeline dot */}
          <div
            className={`absolute left-0 top-1 h-3 w-3 -translate-x-[18px] rounded-full border-2 border-white ${
              action.status === "done" ? "bg-green-500" : "bg-gray-400"
            }`}
          />
          <div className="rounded-lg border bg-card p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-xs font-semibold">{action.action_type}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{action.description}</div>
              </div>
              <span
                className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${
                  STATUS_STYLES[action.status] ?? "bg-gray-100 text-gray-700"
                }`}
              >
                {action.status}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
              {action.assignee_role && <span>담당: {action.assignee_role}</span>}
              {action.due_date && (
                <span>기한: {new Date(action.due_date).toLocaleDateString("ko-KR")}</span>
              )}
              {action.completed_at && (
                <span className="text-green-600">
                  완료: {new Date(action.completed_at).toLocaleDateString("ko-KR")}
                </span>
              )}
            </div>
            {action.result_notes && (
              <div className="mt-1 text-xs text-muted-foreground border-t pt-1">
                {action.result_notes}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
