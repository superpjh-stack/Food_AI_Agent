"use client";

import { useRouter } from "next/navigation";
import { usePurchaseOrders } from "@/lib/hooks/use-purchase-orders";
import { ReceiveChecklist } from "@/components/inventory/receive-checklist";
import { useSiteStore } from "@/lib/stores/site-store";

export default function InventoryReceivePage() {
  const router = useRouter();
  const siteId = useSiteStore((s) => s.currentSite?.id);

  // Load today's approved purchase orders (ready for delivery)
  const { data: poData, isLoading } = usePurchaseOrders({ status: "approved" });
  const approvedOrders = poData?.data ?? [];

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        납품 예정 발주서 로딩 중...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.push("/inventory")}
            className="mb-2 text-xs text-muted-foreground hover:text-foreground"
          >
            &larr; 재고 현황
          </button>
          <h1 className="text-2xl font-bold">입고 검수</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            납품된 식재료를 검수하고 재고를 업데이트합니다. (SAFE-PUR-004)
          </p>
        </div>
      </div>

      {approvedOrders.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed p-10 text-center text-muted-foreground">
          <p className="text-sm">승인된 발주서가 없습니다.</p>
          <p className="mt-1 text-xs">납품 예정 발주서가 없거나 모두 수령 완료되었습니다.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {approvedOrders.map((po) => (
            <div key={po.id} className="rounded-lg border bg-card p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{po.po_number ?? po.id.slice(0, 8)}</h3>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    납품예정: {po.delivery_date} | 금액: {po.total_amount.toLocaleString()}원
                  </p>
                </div>
              </div>
              <ReceiveChecklist
                poId={po.id}
                vendorId={po.vendor_id}
                items={
                  (po.items ?? []).map((item) => ({
                    item_id: item.item_id,
                    item_name: item.item_name,
                    ordered_qty: item.quantity,
                    unit: item.unit,
                    po_item_id: item.id,
                  }))
                }
                onComplete={() => router.push("/inventory")}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
