"use client";

import { useState } from "react";
import { useReceiveInventory } from "@/lib/hooks/use-inventory";
import { useSiteStore } from "@/lib/stores/site-store";

interface ChecklistItem {
  item_id: string;
  item_name: string;
  ordered_qty: number;
  unit: string;
  po_item_id?: string;
}

interface ReceiveChecklistProps {
  items: ChecklistItem[];
  poId?: string;
  vendorId?: string;
  onComplete?: () => void;
}

interface ReceiveEntry {
  item_id: string;
  item_name: string;
  received_qty: string;
  unit: string;
  lot_number: string;
  expiry_date: string;
  storage_temp: string;
  inspect_passed: boolean;
  inspect_note: string;
}

export function ReceiveChecklist({ items, poId, vendorId, onComplete }: ReceiveChecklistProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const receiveInventory = useReceiveInventory();

  const [entries, setEntries] = useState<Record<string, ReceiveEntry>>(
    Object.fromEntries(
      items.map((item) => [
        item.item_id,
        {
          item_id: item.item_id,
          item_name: item.item_name,
          received_qty: String(item.ordered_qty),
          unit: item.unit,
          lot_number: "",
          expiry_date: "",
          storage_temp: "",
          inspect_passed: true,
          inspect_note: "",
        },
      ])
    )
  );

  function updateEntry(itemId: string, field: keyof ReceiveEntry, value: string | boolean) {
    setEntries((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], [field]: value },
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;

    await receiveInventory.mutateAsync({
      site_id: siteId,
      vendor_id: vendorId,
      po_id: poId,
      items: Object.values(entries).map((entry) => ({
        item_id: entry.item_id,
        item_name: entry.item_name,
        received_qty: parseFloat(entry.received_qty) || 0,
        unit: entry.unit,
        lot_number: entry.lot_number || undefined,
        expiry_date: entry.expiry_date || undefined,
        storage_temp: entry.storage_temp ? parseFloat(entry.storage_temp) : undefined,
        inspect_passed: entry.inspect_passed,
        inspect_note: entry.inspect_note || undefined,
      })),
    });

    onComplete?.();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-3 py-2.5 text-left font-medium">품목</th>
              <th className="px-3 py-2.5 text-right font-medium">수령량</th>
              <th className="px-3 py-2.5 text-left font-medium">로트번호</th>
              <th className="px-3 py-2.5 text-left font-medium">유통기한</th>
              <th className="px-3 py-2.5 text-right font-medium">수령온도(°C)</th>
              <th className="px-3 py-2.5 text-center font-medium">검수</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const entry = entries[item.item_id];
              return (
                <tr key={item.item_id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium">{item.item_name}</td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={entry?.received_qty ?? ""}
                      onChange={(e) => updateEntry(item.item_id, "received_qty", e.target.value)}
                      className="w-24 rounded border bg-background px-2 py-1 text-right text-sm"
                      step="0.001"
                      min="0"
                    />
                    <span className="ml-1 text-muted-foreground">{item.unit}</span>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={entry?.lot_number ?? ""}
                      onChange={(e) => updateEntry(item.item_id, "lot_number", e.target.value)}
                      className="w-32 rounded border bg-background px-2 py-1 text-sm"
                      placeholder="LOT-..."
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="date"
                      value={entry?.expiry_date ?? ""}
                      onChange={(e) => updateEntry(item.item_id, "expiry_date", e.target.value)}
                      className="rounded border bg-background px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={entry?.storage_temp ?? ""}
                      onChange={(e) => updateEntry(item.item_id, "storage_temp", e.target.value)}
                      className="w-20 rounded border bg-background px-2 py-1 text-right text-sm"
                      step="0.1"
                      placeholder="4.0"
                    />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input
                      type="checkbox"
                      checked={entry?.inspect_passed ?? true}
                      onChange={(e) =>
                        updateEntry(item.item_id, "inspect_passed", e.target.checked)
                      }
                      className="h-4 w-4 rounded border"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex justify-end gap-2">
        <button
          type="submit"
          disabled={receiveInventory.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {receiveInventory.isPending ? "기록 중..." : "입고 검수 완료"}
        </button>
      </div>
    </form>
  );
}
