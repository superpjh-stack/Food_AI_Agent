"use client";

import { useState } from "react";
import { useSiteStore } from "@/lib/stores/site-store";
import { useCreatePurchaseOrder } from "@/lib/hooks/use-purchase-orders";
import { useVendors } from "@/lib/hooks/use-vendors";

interface PurchaseOrderFormProps {
  bomId?: string;
  onSuccess?: (poId: string) => void;
  onCancel?: () => void;
}

export function PurchaseOrderForm({ bomId, onSuccess, onCancel }: PurchaseOrderFormProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { data: vendorsData } = useVendors({ is_active: true, per_page: 100 });
  const createPO = useCreatePurchaseOrder();

  const today = new Date().toISOString().split("T")[0];
  const [vendorId, setVendorId] = useState("");
  const [orderDate, setOrderDate] = useState(today);
  const [deliveryDate, setDeliveryDate] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const vendors = vendorsData?.data ?? [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !vendorId || !deliveryDate) {
      setError("벤더와 납품예정일을 선택해주세요.");
      return;
    }
    setError(null);

    const result = await createPO.mutateAsync({
      bom_id: bomId,
      site_id: siteId,
      vendor_id: vendorId,
      order_date: orderDate,
      delivery_date: deliveryDate,
      note: note || undefined,
      items: [],
    });

    if ((result as { success: boolean; data?: { id: string } }).success) {
      onSuccess?.((result as { success: boolean; data: { id: string } }).data.id);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-foreground mb-1">
          벤더 선택 <span className="text-destructive">*</span>
        </label>
        <select
          value={vendorId}
          onChange={(e) => setVendorId(e.target.value)}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          required
        >
          <option value="">벤더를 선택하세요</option>
          {vendors.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name} (리드타임: {v.lead_days}일)
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">발주일</label>
          <input
            type="date"
            value={orderDate}
            onChange={(e) => setOrderDate(e.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            납품예정일 <span className="text-destructive">*</span>
          </label>
          <input
            type="date"
            value={deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
            min={orderDate}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">메모</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="발주 관련 특이사항..."
        />
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

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
          disabled={createPO.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {createPO.isPending ? "생성 중..." : "발주서 생성 (초안)"}
        </button>
      </div>
    </form>
  );
}
