"use client";

import { cn } from "@/lib/utils/cn";

interface SSEStep {
  name: string;
  status: "pending" | "started" | "completed" | "error";
  data?: unknown;
}

interface SSEProgressProps {
  steps: SSEStep[];
  isStreaming: boolean;
  textContent: string;
}

export function SSEProgress({ steps, isStreaming, textContent }: SSEProgressProps) {
  return (
    <div className="space-y-4">
      {/* Tool call progress */}
      {steps.length > 0 && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <h4 className="mb-2 text-sm font-medium text-muted-foreground">AI 처리 진행</h4>
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                <StatusIcon status={step.status} />
                <span className={cn(
                  step.status === "completed" && "text-muted-foreground",
                  step.status === "started" && "font-medium",
                  step.status === "error" && "text-destructive",
                )}>
                  {formatToolName(step.name)}
                </span>
                {step.status === "started" && (
                  <span className="ml-1 inline-block h-1 w-1 animate-pulse rounded-full bg-primary" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Streaming text */}
      {textContent && (
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {textContent}
          {isStreaming && <span className="inline-block h-4 w-1 animate-pulse bg-primary" />}
        </div>
      )}

      {/* Loading state */}
      {isStreaming && !textContent && steps.length === 0 && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
          AI가 응답을 생성하고 있습니다...
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: SSEStep["status"] }) {
  switch (status) {
    case "completed":
      return <span className="text-green-500">&#10003;</span>;
    case "started":
      return <span className="text-primary animate-spin">&#9696;</span>;
    case "error":
      return <span className="text-destructive">&#10007;</span>;
    default:
      return <span className="text-muted-foreground">&#9675;</span>;
  }
}

const TOOL_NAME_MAP: Record<string, string> = {
  generate_menu_plan: "식단 생성 중",
  validate_nutrition: "영양 검증 중",
  tag_allergens: "알레르겐 태깅 중",
  check_diversity: "다양성 분석 중",
  search_recipes: "레시피 검색 중",
  scale_recipe: "레시피 스케일링 중",
  generate_haccp_checklist: "HACCP 점검표 생성 중",
  check_haccp_completion: "HACCP 완료 확인 중",
  generate_audit_report: "감사 보고서 생성 중",
  query_dashboard: "대시보드 조회 중",
};

function formatToolName(name: string): string {
  return TOOL_NAME_MAP[name] ?? name;
}
