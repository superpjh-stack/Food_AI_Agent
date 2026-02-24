"use client";

interface Hypothesis {
  hypothesis: string;
  evidence: string[];
  confidence: string;
  safety_note?: string;
  rag_references?: Array<{ title: string; snippet: string; score: number }>;
}

interface RootCauseHypothesisCardProps {
  hypothesis: Hypothesis;
  index: number;
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high:   "border-red-200 bg-red-50",
  medium: "border-yellow-200 bg-yellow-50",
  low:    "border-gray-200 bg-gray-50",
};

export function RootCauseHypothesisCard({ hypothesis, index }: RootCauseHypothesisCardProps) {
  const style = CONFIDENCE_STYLES[hypothesis.confidence] ?? CONFIDENCE_STYLES.low;

  return (
    <div className={`rounded-lg border p-3 ${style}`}>
      <div className="flex items-start gap-2">
        <span className="shrink-0 text-xs font-bold text-muted-foreground">#{index + 1}</span>
        <div className="flex-1 space-y-1">
          <div className="font-medium text-sm">{hypothesis.hypothesis}</div>
          {hypothesis.safety_note && (
            <div className="rounded bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
              {hypothesis.safety_note}
            </div>
          )}
          <div className="space-y-0.5">
            {hypothesis.evidence.map((ev, i) => (
              <div key={i} className="text-xs text-muted-foreground">
                • {ev}
              </div>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            신뢰도:{" "}
            <span
              className={
                hypothesis.confidence === "high"
                  ? "text-red-700 font-medium"
                  : hypothesis.confidence === "medium"
                  ? "text-yellow-700 font-medium"
                  : "text-gray-600"
              }
            >
              {hypothesis.confidence}
            </span>
          </div>
          {hypothesis.rag_references && hypothesis.rag_references.length > 0 && (
            <div className="mt-1 space-y-1 border-t pt-1">
              <div className="text-xs font-medium">유사 사례:</div>
              {hypothesis.rag_references.slice(0, 2).map((ref, i) => (
                <div key={i} className="text-xs text-muted-foreground">
                  {ref.title && <span className="font-medium">{ref.title}: </span>}
                  {ref.snippet.slice(0, 100)}...
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
