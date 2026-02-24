"use client";

import { use, useState } from "react";
import { useClaim, useClaimActions, useAddClaimAction, useUpdateClaimStatus } from "@/lib/hooks/use-claims";
import { ClaimCategoryBadge } from "@/components/claims/claim-category-badge";
import { ClaimSeverityIndicator } from "@/components/claims/claim-severity-indicator";
import { ClaimAnalysisPanel } from "@/components/claims/claim-analysis-panel";
import { ClaimActionTracker } from "@/components/claims/claim-action-tracker";

const STATUS_LABELS: Record<string, string> = {
  open: "미처리",
  investigating: "조사 중",
  action_taken: "조치 완료",
  closed: "종결",
  recurred: "재발",
};

const ACTION_TYPES = [
  "recipe_fix",
  "vendor_warning",
  "staff_training",
  "haccp_update",
  "other",
];

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ClaimDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const { data: claim, isLoading } = useClaim(id);
  const { data: actions } = useClaimActions(id);
  const { mutate: addAction, isPending: addingAction } = useAddClaimAction();
  const { mutate: updateStatus } = useUpdateClaimStatus();

  const [showActionForm, setShowActionForm] = useState(false);
  const [actionForm, setActionForm] = useState({
    action_type: "other",
    description: "",
    assignee_role: "OPS",
    due_date: "",
  });

  if (isLoading) {
    return <div className="p-6 text-muted-foreground">로딩 중...</div>;
  }
  if (!claim) {
    return <div className="p-6 text-muted-foreground">클레임을 찾을 수 없습니다.</div>;
  }

  const handleAddAction = (e: React.FormEvent) => {
    e.preventDefault();
    addAction(
      {
        claimId: id,
        action_type: actionForm.action_type,
        description: actionForm.description,
        assignee_role: actionForm.assignee_role,
        due_date: actionForm.due_date || undefined,
      },
      {
        onSuccess: () => {
          setShowActionForm(false);
          setActionForm({ action_type: "other", description: "", assignee_role: "OPS", due_date: "" });
        },
      }
    );
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <ClaimCategoryBadge category={claim.category} />
          <ClaimSeverityIndicator severity={claim.severity} />
          <span className="text-xs text-muted-foreground">
            {STATUS_LABELS[claim.status] ?? claim.status}
          </span>
          {claim.is_recurring && (
            <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">
              재발 {claim.recurrence_count}회
            </span>
          )}
        </div>
        <h1 className="text-xl font-bold">{claim.title}</h1>
        <p className="text-sm text-muted-foreground">
          {new Date(claim.incident_date).toLocaleString("ko-KR")}
          {claim.reporter_name && ` · 접수: ${claim.reporter_name} (${claim.reporter_role})`}
        </p>
      </div>

      <div className="rounded-lg border bg-card p-4">
        <h2 className="mb-2 font-semibold text-sm">상황 설명</h2>
        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{claim.description}</p>
      </div>

      {/* Status actions */}
      <div className="flex flex-wrap gap-2">
        {claim.status === "open" && (
          <button
            onClick={() => updateStatus({ claimId: id, status: "investigating" })}
            className="rounded border px-3 py-1 text-xs hover:bg-muted"
          >
            조사 시작
          </button>
        )}
        {claim.status !== "closed" && (
          <button
            onClick={() => updateStatus({ claimId: id, status: "closed" })}
            className="rounded border border-green-300 px-3 py-1 text-xs text-green-700 hover:bg-green-50"
          >
            종결 처리
          </button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* AI Analysis */}
        <div className="rounded-lg border bg-card p-4">
          <ClaimAnalysisPanel
            claimId={id}
            hypotheses={claim.ai_hypotheses}
            relatedData={undefined}
          />
        </div>

        {/* Actions */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">조치 이력</h3>
            <button
              onClick={() => setShowActionForm(!showActionForm)}
              className="rounded bg-primary px-2 py-1 text-xs font-medium text-primary-foreground"
            >
              조치 추가
            </button>
          </div>

          {showActionForm && (
            <form onSubmit={handleAddAction} className="space-y-2 border rounded p-3 bg-muted/30">
              <div>
                <label className="text-xs text-muted-foreground">조치 유형</label>
                <select
                  className="w-full rounded border px-2 py-1 text-sm"
                  value={actionForm.action_type}
                  onChange={(e) => setActionForm({ ...actionForm, action_type: e.target.value })}
                >
                  {ACTION_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">내용</label>
                <textarea
                  className="w-full rounded border px-2 py-1 text-sm"
                  rows={2}
                  value={actionForm.description}
                  onChange={(e) => setActionForm({ ...actionForm, description: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-muted-foreground">담당 역할</label>
                  <select
                    className="w-full rounded border px-2 py-1 text-sm"
                    value={actionForm.assignee_role}
                    onChange={(e) => setActionForm({ ...actionForm, assignee_role: e.target.value })}
                  >
                    {["NUT", "PUR", "KIT", "QLT", "OPS", "CS"].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">기한</label>
                  <input
                    type="datetime-local"
                    className="w-full rounded border px-2 py-1 text-sm"
                    value={actionForm.due_date}
                    onChange={(e) => setActionForm({ ...actionForm, due_date: e.target.value })}
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={addingAction}
                className="w-full rounded bg-primary px-2 py-1 text-xs font-medium text-primary-foreground disabled:opacity-50"
              >
                {addingAction ? "등록 중..." : "조치 등록"}
              </button>
            </form>
          )}

          <ClaimActionTracker actions={Array.isArray(actions) ? actions : []} />
        </div>
      </div>
    </div>
  );
}
