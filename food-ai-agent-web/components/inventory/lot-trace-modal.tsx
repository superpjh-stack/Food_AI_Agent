"use client";

import { useState } from "react";
import { useTraceLot } from "@/lib/hooks/use-inventory";

interface LotTraceModalProps {
  lotId: string;
  lotNumber?: string;
  itemName?: string;
  onClose: () => void;
}

interface TraceResult {
  lot_id: string;
  lot_number?: string;
  item_name: string;
  received_at: string;
  expiry_date?: string;
  status: string;
  total_quantity: number;
  remaining_qty: number;
  total_used_qty: number;
  used_in_menus: Array<{
    menu_plan_id: string;
    date: string;
    used_qty: number;
  }>;
  inspect_result: Record<string, unknown>;
  trace_note: string;
}

export function LotTraceModal({ lotId, lotNumber, itemName, onClose }: LotTraceModalProps) {
  const traceLot = useTraceLot();
  const [traceResult, setTraceResult] = useState<TraceResult | null>(null);

  async function handleTrace() {
    const result = await traceLot.mutateAsync(lotId);
    setTraceResult((result as { data: TraceResult }).data ?? null);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-xl bg-card p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">로트 추적</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {itemName} {lotNumber && `· 로트 ${lotNumber}`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-muted"
          >
            X
          </button>
        </div>

        {!traceResult && (
          <div className="text-center">
            <p className="mb-4 text-sm text-muted-foreground">
              이 로트가 어느 식단/현장에서 사용됐는지 추적합니다. (SAFE-PUR-004)
            </p>
            <button
              onClick={handleTrace}
              disabled={traceLot.isPending}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {traceLot.isPending ? "추적 중..." : "로트 추적 시작"}
            </button>
          </div>
        )}

        {traceResult && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">입고량</p>
                <p className="mt-1 font-semibold">{traceResult.total_quantity}</p>
              </div>
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">잔여량</p>
                <p className="mt-1 font-semibold">{traceResult.remaining_qty}</p>
              </div>
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">사용량</p>
                <p className="mt-1 font-semibold">{traceResult.total_used_qty}</p>
              </div>
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">상태</p>
                <p className="mt-1 font-semibold">{traceResult.status}</p>
              </div>
            </div>

            {traceResult.used_in_menus.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">사용 이력</h4>
                <div className="space-y-1.5">
                  {traceResult.used_in_menus.map((use, i) => (
                    <div key={i} className="flex items-center justify-between rounded-md bg-muted/30 px-3 py-2 text-xs">
                      <span>{use.date}</span>
                      <span className="font-medium">사용량: {use.used_qty}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-700">
              {traceResult.trace_note}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
