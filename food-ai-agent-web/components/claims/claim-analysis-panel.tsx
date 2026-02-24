"use client";

import { useAnalyzeClaim } from "@/lib/hooks/use-claims";
import { RootCauseHypothesisCard } from "./root-cause-hypothesis-card";

interface ClaimAnalysisPanelProps {
  claimId: string;
  hypotheses: Array<Record<string, unknown>>;
  relatedData?: Record<string, unknown>;
}

export function ClaimAnalysisPanel({ claimId, hypotheses, relatedData }: ClaimAnalysisPanelProps) {
  const { mutate: analyze, isPending } = useAnalyzeClaim();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">AI 원인 분석</h3>
        <button
          onClick={() => analyze({ claimId, useRag: true })}
          disabled={isPending}
          className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-50 hover:bg-indigo-700"
        >
          {isPending ? "분석 중..." : "AI 분석 재실행"}
        </button>
      </div>

      {hypotheses.length > 0 ? (
        <div className="space-y-2">
          {hypotheses.map((h, i) => (
            <RootCauseHypothesisCard
              key={i}
              hypothesis={h as {
                hypothesis: string;
                evidence: string[];
                confidence: string;
                safety_note?: string;
              }}
              index={i}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
          AI 분석 결과가 없습니다. 위 버튼을 눌러 분석을 실행하세요.
        </div>
      )}

      {relatedData && Object.keys(relatedData).length > 0 && (
        <div className="rounded-lg border bg-muted/30 p-3">
          <div className="mb-2 text-xs font-semibold">연관 데이터</div>
          {relatedData.menu_plan && (
            <div className="text-xs text-muted-foreground">
              식단: {(relatedData.menu_plan as Record<string, string>).title}
            </div>
          )}
          {relatedData.recipe && (
            <div className="text-xs text-muted-foreground">
              레시피: {(relatedData.recipe as Record<string, string>).name}
            </div>
          )}
          {relatedData.lot_number && (
            <div className="text-xs text-muted-foreground">
              로트: {String(relatedData.lot_number)}
            </div>
          )}
          {relatedData.recent_haccp_incidents && (
            <div className="text-xs text-muted-foreground">
              최근 HACCP 사고: {(relatedData.recent_haccp_incidents as unknown[]).length}건
            </div>
          )}
        </div>
      )}
    </div>
  );
}
