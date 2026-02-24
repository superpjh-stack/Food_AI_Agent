"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";

interface ChecklistItemProps {
  item: {
    item: string;
    category: string;
    is_ccp: boolean;
    target?: string;
  };
  index: number;
  onRecordSubmit: (record: {
    ccp_point: string;
    category: string;
    target_value?: string;
    actual_value: string;
    is_compliant: boolean;
    corrective_action?: string;
  }) => void;
  existingRecord?: {
    actual_value?: string;
    is_compliant?: boolean;
    corrective_action?: string;
  };
}

export function ChecklistItem({ item, index, onRecordSubmit, existingRecord }: ChecklistItemProps) {
  const [checked, setChecked] = useState(!!existingRecord);
  const [actualValue, setActualValue] = useState(existingRecord?.actual_value ?? "");
  const [isCompliant, setIsCompliant] = useState(existingRecord?.is_compliant ?? true);
  const [correctiveAction, setCorrectiveAction] = useState(existingRecord?.corrective_action ?? "");
  const [expanded, setExpanded] = useState(false);

  const handleSubmit = () => {
    onRecordSubmit({
      ccp_point: item.item,
      category: item.category,
      target_value: item.target,
      actual_value: item.is_ccp ? actualValue : "checked",
      is_compliant: isCompliant,
      corrective_action: !isCompliant ? correctiveAction : undefined,
    });
    setChecked(true);
    setExpanded(false);
  };

  if (!item.is_ccp) {
    // Simple checkbox item
    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-lg border p-3",
          checked ? "border-green-200 bg-green-50" : "border-border",
        )}
      >
        <button
          onClick={() => {
            if (!checked) {
              handleSubmit();
            }
          }}
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded border-2",
            checked
              ? "border-green-500 bg-green-500 text-white"
              : "border-gray-300 hover:border-primary",
          )}
        >
          {checked && "\u2713"}
        </button>
        <div className="flex-1">
          <span className={cn("text-sm", checked && "text-muted-foreground line-through")}>
            {index + 1}. {item.item}
          </span>
          <span className="ml-2 text-xs text-muted-foreground">({item.category})</span>
        </div>
      </div>
    );
  }

  // CCP item with measurement input
  return (
    <div
      className={cn(
        "rounded-lg border-2 p-3",
        checked
          ? isCompliant
            ? "border-green-300 bg-green-50"
            : "border-red-300 bg-red-50"
          : "border-red-200",
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 text-left"
      >
        <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">CCP</span>
        <div className="flex-1">
          <span className="text-sm font-medium">{index + 1}. {item.item}</span>
          {item.target && (
            <span className="ml-2 text-xs text-muted-foreground">Target: {item.target}</span>
          )}
        </div>
        {checked && (
          <span className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            isCompliant ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700",
          )}>
            {isCompliant ? "Pass" : "Fail"}
          </span>
        )}
      </button>

      {expanded && !checked && (
        <div className="mt-3 space-y-3 border-t pt-3">
          <div>
            <label className="block text-xs font-medium">Actual Value</label>
            <input
              type="text"
              value={actualValue}
              onChange={(e) => setActualValue(e.target.value)}
              className="mt-1 block w-full rounded-md border bg-background px-3 py-1.5 text-sm"
              placeholder={item.target ? `Target: ${item.target}` : "Enter measurement"}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setIsCompliant(true)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium",
                isCompliant ? "bg-green-600 text-white" : "border bg-background",
              )}
            >
              Pass
            </button>
            <button
              onClick={() => setIsCompliant(false)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium",
                !isCompliant ? "bg-red-600 text-white" : "border bg-background",
              )}
            >
              Fail
            </button>
          </div>
          {!isCompliant && (
            <div>
              <label className="block text-xs font-medium">Corrective Action</label>
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
            onClick={handleSubmit}
            disabled={!actualValue}
            className="w-full rounded-md bg-primary py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            Save Record
          </button>
        </div>
      )}
    </div>
  );
}
