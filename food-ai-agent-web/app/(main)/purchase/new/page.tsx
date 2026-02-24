"use client";

import { useRouter } from "next/navigation";
import { PurchaseOrderForm } from "@/components/purchase/purchase-order-form";

export default function NewPurchaseOrderPage() {
  const router = useRouter();

  function handleSuccess(poId: string) {
    router.push(`/purchase/${poId}`);
  }

  function handleCancel() {
    router.back();
  }

  return (
    <div className="mx-auto max-w-xl p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">발주서 직접 생성</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          BOM 없이 발주서를 직접 작성합니다. 초안으로 저장 후 OPS 승인이 필요합니다.
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <PurchaseOrderForm onSuccess={handleSuccess} onCancel={handleCancel} />
      </div>

      <div className="mt-4 rounded-md bg-amber-50 px-4 py-3 text-xs text-amber-700">
        발주 확정(제출)은 반드시 OPS 승인 후 진행됩니다. (SAFE-PUR-001)
      </div>
    </div>
  );
}
