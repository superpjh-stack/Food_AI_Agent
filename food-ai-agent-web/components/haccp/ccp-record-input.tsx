"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";

interface CcpRecordInputProps {
  ccpPoint: string;
  target: string;
  category: string;
  onSubmit: (record: {
    actual_value: string;
    is_compliant: boolean;
    corrective_action?: string;
  }) => void;
  isLoading: boolean;
}

export function CcpRecordInput({ ccpPoint, target, category, onSubmit, isLoading }: CcpRecordInputProps) {
  const [actualValue, setActualValue] = useState("");
  const [isCompliant, setIsCompliant] = useState(true);
  const [correctiveAction, setCorrectiveAction] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      actual_value: actualValue,
      is_compliant: isCompliant,
      corrective_action: !isCompliant ? correctiveAction : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border-2 border-red-200 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">CCP</span>
        <span className="text-sm font-medium">{ccpPoint}</span>
      </div>
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span>Category: {category}</span>
        <span>Target: {target}</span>
      </div>

      <div>
        <label className="block text-xs font-medium">Measured Value</label>
        <input
          type="text"
          value={actualValue}
          onChange={(e) => setActualValue(e.target.value)}
          className="mt-1 block w-full rounded-md border bg-background px-3 py-1.5 text-sm"
          placeholder={`Target: ${target}`}
          required
        />
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setIsCompliant(true)}
          className={cn(
            "flex-1 rounded-md py-1.5 text-sm font-medium",
            isCompliant ? "bg-green-600 text-white" : "border bg-background text-muted-foreground",
          )}
        >
          Pass
        </button>
        <button
          type="button"
          onClick={() => setIsCompliant(false)}
          className={cn(
            "flex-1 rounded-md py-1.5 text-sm font-medium",
            !isCompliant ? "bg-red-600 text-white" : "border bg-background text-muted-foreground",
          )}
        >
          Fail
        </button>
      </div>

      {!isCompliant && (
        <div>
          <label className="block text-xs font-medium">Corrective Action (required)</label>
          <textarea
            value={correctiveAction}
            onChange={(e) => setCorrectiveAction(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-1.5 text-sm"
            rows={2}
            required
          />
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading || !actualValue}
        className="w-full rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {isLoading ? "Saving..." : "Save Record"}
      </button>
    </form>
  );
}
