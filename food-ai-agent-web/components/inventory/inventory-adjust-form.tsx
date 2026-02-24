"use client";

import { useState } from "react";
import { useAdjustInventory } from "@/lib/hooks/use-inventory";
import { useSiteStore } from "@/lib/stores/site-store";

interface InventoryAdjustFormProps {
  itemId: string;
  itemName: string;
  currentQty: number;
  unit: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function InventoryAdjustForm({
  itemId,
  itemName,
  currentQty,
  unit,
  onSuccess,
  onCancel,
}: InventoryAdjustFormProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const adjustInventory = useAdjustInventory();
  const [quantity, setQuantity] = useState(String(currentQty));
  const [reason, setReason] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    await adjustInventory.mutateAsync({
      itemId,
      siteId,
      quantity: parseFloat(quantity),
      reason: reason || undefined,
    });
    onSuccess?.();
  }

  const diff = parseFloat(quantity) - currentQty;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <p className="text-sm font-medium text-foreground">{itemName}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          현재 재고: {currentQty.toLocaleString()} {unit}
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">
          실사 수량 ({unit})
        </label>
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          step="0.001"
          min="0"
          required
        />
        {quantity && !isNaN(diff) && diff !== 0 && (
          <p className={`mt-1 text-xs ${diff > 0 ? "text-green-600" : "text-red-600"}`}>
            차이: {diff > 0 ? "+" : ""}{diff.toFixed(3)} {unit}
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">조정 사유</label>
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="재고실사, 폐기, 사용 등..."
        />
      </div>

      <div className="flex justify-end gap-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
          >
            취소
          </button>
        )}
        <button
          type="submit"
          disabled={adjustInventory.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {adjustInventory.isPending ? "저장 중..." : "재고 조정"}
        </button>
      </div>
    </form>
  );
}
