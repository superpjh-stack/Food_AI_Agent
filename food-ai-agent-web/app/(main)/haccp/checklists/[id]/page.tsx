"use client";

import { useParams } from "next/navigation";
import { useHACCPChecklist, useCreateCCPRecord, useSubmitChecklist } from "@/lib/hooks/use-haccp";
import { ChecklistItem } from "@/components/haccp/checklist-item";

export default function ChecklistDetailPage() {
  const params = useParams();
  const checklistId = params.id as string;
  const { data: checklist, isLoading } = useHACCPChecklist(checklistId);
  const createRecord = useCreateCCPRecord();
  const submitChecklist = useSubmitChecklist();

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        Loading checklist...
      </div>
    );
  }

  if (!checklist) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        Checklist not found.
      </div>
    );
  }

  const template = (checklist.template as { item: string; category: string; is_ccp: boolean; target?: string }[]) ?? [];
  const records = (checklist as unknown as { records: { ccp_point: string; actual_value?: string; is_compliant?: boolean; corrective_action?: string }[] }).records ?? [];

  const handleRecordSubmit = async (record: {
    ccp_point: string;
    category: string;
    target_value?: string;
    actual_value: string;
    is_compliant: boolean;
    corrective_action?: string;
  }) => {
    await createRecord.mutateAsync({
      checklist_id: checklistId,
      ccp_point: record.ccp_point,
      category: record.category,
      target_value: record.target_value,
      actual_value: record.actual_value,
      is_compliant: record.is_compliant,
      corrective_action: record.corrective_action,
    });
  };

  const handleSubmitChecklist = async () => {
    await submitChecklist.mutateAsync(checklistId);
  };

  const isOverdue = checklist.status === "overdue" || checklist.status === "pending";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            {checklist.checklist_type === "daily" ? "Daily" : "Weekly"} Checklist
          </h1>
          <p className="text-sm text-muted-foreground">
            {checklist.date} {checklist.meal_type ? `/ ${checklist.meal_type}` : ""}
          </p>
        </div>
        {checklist.status !== "completed" && (
          <button
            onClick={handleSubmitChecklist}
            disabled={submitChecklist.isPending}
            className={`rounded-md px-4 py-2 text-sm font-medium text-white ${
              isOverdue
                ? "bg-red-600 hover:bg-red-700"
                : "bg-green-600 hover:bg-green-700"
            } disabled:opacity-50`}
          >
            {submitChecklist.isPending ? "Submitting..." : "Submit Checklist"}
          </button>
        )}
      </div>

      {/* Items */}
      <div className="space-y-2">
        {template.map((item, idx) => {
          const existingRecord = records.find((r) => r.ccp_point === item.item);
          return (
            <ChecklistItem
              key={idx}
              item={item}
              index={idx}
              onRecordSubmit={handleRecordSubmit}
              existingRecord={existingRecord}
            />
          );
        })}
      </div>
    </div>
  );
}
