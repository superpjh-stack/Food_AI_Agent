"use client";

import { useState } from "react";
import { useHACCPChecklists, useGenerateChecklist } from "@/lib/hooks/use-haccp";
import { ChecklistForm } from "@/components/haccp/checklist-form";
import { cn } from "@/lib/utils/cn";
import Link from "next/link";

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "bg-gray-100 text-gray-700" },
  in_progress: { label: "In Progress", color: "bg-blue-100 text-blue-700" },
  completed: { label: "Completed", color: "bg-green-100 text-green-700" },
  overdue: { label: "Overdue", color: "bg-red-100 text-red-700" },
};

export default function ChecklistsPage() {
  const [showForm, setShowForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const { data, isLoading } = useHACCPChecklists({ status: statusFilter || undefined });
  const generateMutation = useGenerateChecklist();

  const checklists = (data as unknown as { data: unknown[] })?.data ?? [];

  const handleGenerate = async (params: {
    site_id: string;
    date: string;
    checklist_type: string;
    meal_type?: string;
  }) => {
    await generateMutation.mutateAsync(params);
    setShowForm(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">HACCP Checklists</h1>
          <p className="text-sm text-muted-foreground">Manage daily and weekly inspection checklists</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          + Generate Checklist
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {["", "pending", "in_progress", "completed", "overdue"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium",
              statusFilter === s
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">Loading...</div>
      ) : checklists.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          No checklists found.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left font-medium">Date</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Meal</th>
                <th className="px-4 py-3 text-left font-medium">Items</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {checklists.map((cl: Record<string, unknown>) => {
                const status = STATUS_STYLES[(cl.status as string) ?? "pending"];
                const template = (cl.template as unknown[]) ?? [];
                return (
                  <tr key={cl.id as string} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <Link
                        href={`/haccp/checklists/${cl.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {cl.date as string}
                      </Link>
                    </td>
                    <td className="px-4 py-3 capitalize text-muted-foreground">
                      {cl.checklist_type as string}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {(cl.meal_type as string) ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {template.length} items
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", status?.color)}>
                        {status?.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <ChecklistForm
          onSubmit={handleGenerate}
          isLoading={generateMutation.isPending}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
