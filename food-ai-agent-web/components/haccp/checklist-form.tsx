"use client";

import { useState } from "react";
import { useSiteStore } from "@/lib/stores/site-store";

interface ChecklistFormProps {
  onSubmit: (params: {
    site_id: string;
    date: string;
    checklist_type: string;
    meal_type?: string;
  }) => void;
  isLoading: boolean;
  onClose: () => void;
}

export function ChecklistForm({ onSubmit, isLoading, onClose }: ChecklistFormProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [type, setType] = useState("daily");
  const [mealType, setMealType] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteId) return;
    onSubmit({
      site_id: siteId,
      date,
      checklist_type: type,
      meal_type: mealType || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-card p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold">Generate HACCP Checklist</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
          {type === "daily" && (
            <div>
              <label className="block text-sm font-medium">Meal Type (optional)</label>
              <select
                value={mealType}
                onChange={(e) => setMealType(e.target.value)}
                className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="">General</option>
                <option value="breakfast">Breakfast</option>
                <option value="lunch">Lunch</option>
                <option value="dinner">Dinner</option>
              </select>
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isLoading ? "Generating..." : "Generate"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-md border py-2 text-sm font-medium hover:bg-muted/50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
