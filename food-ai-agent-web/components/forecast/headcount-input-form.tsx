"use client";

import { useState } from "react";
import { useRecordActual } from "@/lib/hooks/use-forecast";
import { useSiteStore } from "@/lib/stores/site-store";

const MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"];

export function HeadcountInputForm() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { mutate: recordActual, isPending } = useRecordActual();

  const [form, setForm] = useState({
    record_date: new Date().toISOString().slice(0, 10),
    meal_type: "lunch",
    planned: "",
    actual: "",
    served: "",
    notes: "",
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteId) return;
    recordActual(
      {
        site_id: siteId,
        record_date: form.record_date,
        meal_type: form.meal_type,
        planned: Number(form.planned),
        actual: Number(form.actual),
        served: form.served ? Number(form.served) : undefined,
        notes: form.notes || undefined,
      },
      {
        onSuccess: () => {
          setSubmitted(true);
          setTimeout(() => setSubmitted(false), 3000);
        },
      }
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border bg-card p-4">
      <h3 className="font-semibold text-sm">실제 식수 입력</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground">날짜</label>
          <input
            type="date"
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.record_date}
            onChange={(e) => setForm({ ...form, record_date: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">식사 구분</label>
          <select
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.meal_type}
            onChange={(e) => setForm({ ...form, meal_type: e.target.value })}
          >
            {MEAL_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">계획 식수</label>
          <input
            type="number"
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.planned}
            onChange={(e) => setForm({ ...form, planned: e.target.value })}
            required
            min={0}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">실제 식수</label>
          <input
            type="number"
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.actual}
            onChange={(e) => setForm({ ...form, actual: e.target.value })}
            required
            min={0}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">배식 인원 (선택)</label>
          <input
            type="number"
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.served}
            onChange={(e) => setForm({ ...form, served: e.target.value })}
            min={0}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">메모</label>
          <input
            type="text"
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {isPending ? "저장 중..." : "실적 저장"}
      </button>
      {submitted && (
        <p className="text-center text-xs text-green-600">저장 완료!</p>
      )}
    </form>
  );
}
