"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";

interface CcpPoint {
  type: string;
  target: string;
  critical: boolean;
}

interface CcpInputProps {
  ccpPoints: { step_order: number; ccp: CcpPoint }[];
  onSubmit: (records: CcpRecord[]) => void;
}

interface CcpRecord {
  step_order: number;
  ccp_type: string;
  target: string;
  actual_value: string;
  is_compliant: boolean;
  corrective_action: string;
}

export function CcpInput({ ccpPoints, onSubmit }: CcpInputProps) {
  const [records, setRecords] = useState<CcpRecord[]>(
    ccpPoints.map((p) => ({
      step_order: p.step_order,
      ccp_type: p.ccp.type,
      target: p.ccp.target,
      actual_value: "",
      is_compliant: true,
      corrective_action: "",
    }))
  );

  const updateRecord = (idx: number, updates: Partial<CcpRecord>) => {
    setRecords((prev) => prev.map((r, i) => (i === idx ? { ...r, ...updates } : r)));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(records);
  };

  if (ccpPoints.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">No CCP points for this work order.</div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="font-semibold">CCP Records</h3>

      {records.map((record, idx) => (
        <div
          key={idx}
          className={cn(
            "rounded-lg border p-4 space-y-3",
            !record.is_compliant ? "border-red-300 bg-red-50" : "border-border",
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium">Step {record.step_order}</span>
              <span className="ml-2 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                {record.ccp_type}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">Target: {record.target}</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium">Actual Value</label>
              <input
                type="text"
                value={record.actual_value}
                onChange={(e) => updateRecord(idx, { actual_value: e.target.value })}
                className="mt-1 block w-full rounded-md border bg-background px-3 py-1.5 text-sm"
                placeholder="e.g. 75°C"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Compliant?</label>
              <div className="mt-1 flex gap-2">
                <button
                  type="button"
                  onClick={() => updateRecord(idx, { is_compliant: true })}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium",
                    record.is_compliant
                      ? "bg-green-600 text-white"
                      : "border bg-background text-muted-foreground",
                  )}
                >
                  Pass
                </button>
                <button
                  type="button"
                  onClick={() => updateRecord(idx, { is_compliant: false })}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium",
                    !record.is_compliant
                      ? "bg-red-600 text-white"
                      : "border bg-background text-muted-foreground",
                  )}
                >
                  Fail
                </button>
              </div>
            </div>
          </div>

          {!record.is_compliant && (
            <div>
              <label className="block text-xs font-medium">Corrective Action</label>
              <textarea
                value={record.corrective_action}
                onChange={(e) => updateRecord(idx, { corrective_action: e.target.value })}
                className="mt-1 block w-full rounded-md border bg-background px-3 py-1.5 text-sm"
                rows={2}
                required
              />
            </div>
          )}
        </div>
      ))}

      <button
        type="submit"
        className="w-full rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        Save CCP Records
      </button>
    </form>
  );
}
