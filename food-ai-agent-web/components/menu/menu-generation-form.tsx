"use client";

import { useState } from "react";

interface MenuGenerationFormProps {
  onSubmit: (params: MenuGenerationParams) => void;
  isLoading: boolean;
}

export interface MenuGenerationParams {
  site_id: string;
  period_start: string;
  period_end: string;
  meal_types: string[];
  target_headcount: number;
  budget_per_meal?: number;
  preferences?: string;
}

const MEAL_TYPES = [
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "dinner", label: "Dinner" },
  { value: "snack", label: "Snack" },
];

export function MenuGenerationForm({ onSubmit, isLoading }: MenuGenerationFormProps) {
  const [siteId, setSiteId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [mealTypes, setMealTypes] = useState<string[]>(["lunch"]);
  const [headcount, setHeadcount] = useState(350);
  const [budget, setBudget] = useState<number | undefined>(3500);
  const [preferences, setPreferences] = useState("");

  const toggleMealType = (type: string) => {
    setMealTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      site_id: siteId,
      period_start: periodStart,
      period_end: periodEnd,
      meal_types: mealTypes,
      target_headcount: headcount,
      budget_per_meal: budget,
      preferences: preferences || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium">Site</label>
          <select
            value={siteId}
            onChange={(e) => setSiteId(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            required
          >
            <option value="">Select site...</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Headcount</label>
          <input
            type="number"
            value={headcount}
            onChange={(e) => setHeadcount(Number(e.target.value))}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            min={1}
            required
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium">Start Date</label>
          <input
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium">End Date</label>
          <input
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium">Meal Types</label>
        <div className="mt-1 flex flex-wrap gap-2">
          {MEAL_TYPES.map((mt) => (
            <button
              key={mt.value}
              type="button"
              onClick={() => toggleMealType(mt.value)}
              className={`rounded-full border px-3 py-1 text-sm ${
                mealTypes.includes(mt.value)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground"
              }`}
            >
              {mt.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium">Budget per Meal (KRW)</label>
        <input
          type="number"
          value={budget ?? ""}
          onChange={(e) => setBudget(e.target.value ? Number(e.target.value) : undefined)}
          className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="e.g. 3500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Preferences / Restrictions</label>
        <textarea
          value={preferences}
          onChange={(e) => setPreferences(e.target.value)}
          className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
          rows={2}
          placeholder="e.g. Exclude seafood, prefer Korean cuisine..."
        />
      </div>

      <button
        type="submit"
        disabled={isLoading || !siteId || !periodStart || !periodEnd || mealTypes.length === 0}
        className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {isLoading ? "AI Generating..." : "Generate Menu Plan"}
      </button>
    </form>
  );
}
