"use client";

import { useState } from "react";
import { useCreateWasteRecord } from "@/lib/hooks/use-waste";
import { useSiteStore } from "@/lib/stores/site-store";

interface WasteItem {
  item_name: string;
  waste_pct: string;
  served_count: string;
  recipe_id: string;
}

export function WasteInputForm() {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { mutate: createWaste, isPending } = useCreateWasteRecord();

  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [mealType, setMealType] = useState("lunch");
  const [items, setItems] = useState<WasteItem[]>([
    { item_name: "", waste_pct: "", served_count: "", recipe_id: "" },
  ]);
  const [submitted, setSubmitted] = useState(false);

  const addRow = () =>
    setItems([...items, { item_name: "", waste_pct: "", served_count: "", recipe_id: "" }]);

  const removeRow = (idx: number) =>
    setItems(items.filter((_, i) => i !== idx));

  const updateRow = (idx: number, field: keyof WasteItem, value: string) => {
    const updated = [...items];
    updated[idx] = { ...updated[idx], [field]: value };
    setItems(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteId) return;

    const wasteItems = items
      .filter((i) => i.item_name.trim())
      .map((i) => ({
        item_name: i.item_name,
        waste_pct: i.waste_pct ? Number(i.waste_pct) : undefined,
        served_count: i.served_count ? Number(i.served_count) : undefined,
        recipe_id: i.recipe_id || undefined,
      }));

    createWaste(
      { site_id: siteId, record_date: date, meal_type: mealType, items: wasteItems },
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
      <h3 className="font-semibold text-sm">잔반 입력</h3>
      <div className="flex gap-3">
        <div>
          <label className="text-xs text-muted-foreground">날짜</label>
          <input
            type="date"
            className="block rounded border px-2 py-1 text-sm"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">식사</label>
          <select
            className="block rounded border px-2 py-1 text-sm"
            value={mealType}
            onChange={(e) => setMealType(e.target.value)}
          >
            {["breakfast", "lunch", "dinner", "snack"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="pb-1 text-left font-medium">메뉴명</th>
              <th className="pb-1 text-left font-medium">잔반률 (%)</th>
              <th className="pb-1 text-left font-medium">배식 인원</th>
              <th className="pb-1 text-left font-medium">레시피 ID</th>
              <th />
            </tr>
          </thead>
          <tbody className="space-y-1">
            {items.map((item, idx) => (
              <tr key={idx} className="border-b last:border-0">
                <td className="py-1 pr-2">
                  <input
                    className="w-full rounded border px-2 py-1"
                    value={item.item_name}
                    onChange={(e) => updateRow(idx, "item_name", e.target.value)}
                    placeholder="메뉴명"
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    type="number"
                    className="w-20 rounded border px-2 py-1"
                    value={item.waste_pct}
                    onChange={(e) => updateRow(idx, "waste_pct", e.target.value)}
                    min={0}
                    max={100}
                    placeholder="0-100"
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    type="number"
                    className="w-20 rounded border px-2 py-1"
                    value={item.served_count}
                    onChange={(e) => updateRow(idx, "served_count", e.target.value)}
                    min={0}
                    placeholder="인원"
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    className="w-32 rounded border px-2 py-1"
                    value={item.recipe_id}
                    onChange={(e) => updateRow(idx, "recipe_id", e.target.value)}
                    placeholder="UUID (선택)"
                  />
                </td>
                <td className="py-1">
                  <button
                    type="button"
                    onClick={() => removeRow(idx)}
                    className="text-red-500 hover:text-red-700"
                  >
                    X
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={addRow}
        className="text-xs text-primary underline"
      >
        + 메뉴 추가
      </button>

      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {isPending ? "저장 중..." : "잔반 저장"}
      </button>
      {submitted && (
        <p className="text-center text-xs text-green-600">저장 완료!</p>
      )}
    </form>
  );
}
