"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  usePurchaseOrder,
  useSubmitPurchaseOrder,
  useApprovePurchaseOrder,
  useCancelPurchaseOrder,
} from "@/lib/hooks/use-purchase-orders";
import { POStatusBadge } from "@/components/purchase/po-status-badge";

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const poId = params.id as string;

  const { data: poData, isLoading } = usePurchaseOrder(poId);
  const submitPO = useSubmitPurchaseOrder();
  const approvePO = useApprovePurchaseOrder();
  const cancelPO = useCancelPurchaseOrder();

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const po = (poData as { data?: typeof poData } | typeof poData)?.data ?? poData;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        로딩 중...
      </div>
    );
  }

  if (!po || !(po as { id?: string }).id) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">발주서를 찾을 수 없습니다.</p>
          <button
            onClick={() => router.push("/purchase")}
            className="mt-2 text-sm text-primary hover:underline"
          >
            목록으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  const order = po as {
    id: string;
    po_number?: string;
    status: string;
    order_date: string;
    delivery_date: string;
    total_amount: number;
    tax_amount: number;
    note?: string;
    items?: Array<{
      id: string;
      item_name: string;
      quantity: number;
      unit: string;
      unit_price: number;
      subtotal: number;
    }>;
  };

  async function handleSubmit() {
    await submitPO.mutateAsync({ poId });
  }

  async function handleApprove() {
    await approvePO.mutateAsync({ poId });
  }

  async function handleCancel() {
    if (!cancelReason.trim()) return;
    await cancelPO.mutateAsync({ poId, cancel_reason: cancelReason });
    setShowCancelModal(false);
  }

  return (
    <div className="mx-auto max-w-3xl p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.push("/purchase")}
            className="mb-2 text-xs text-muted-foreground hover:text-foreground"
          >
            &larr; 발주 목록
          </button>
          <h1 className="text-2xl font-bold">
            {order.po_number ?? "발주서"}
          </h1>
        </div>
        <POStatusBadge status={order.status as "draft" | "submitted" | "approved" | "received" | "cancelled"} />
      </div>

      {/* Summary */}
      <div className="rounded-lg border bg-card p-5 grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-xs text-muted-foreground">발주일</p>
          <p className="mt-1 font-medium">{order.order_date}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">납품예정일</p>
          <p className="mt-1 font-medium">{order.delivery_date}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">공급가액</p>
          <p className="mt-1 font-semibold text-primary">{order.total_amount.toLocaleString()}원</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">부가세 (10%)</p>
          <p className="mt-1 font-medium">{order.tax_amount.toLocaleString()}원</p>
        </div>
      </div>

      {/* Items */}
      {(order.items ?? []).length > 0 && (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left font-medium">품목</th>
                <th className="px-4 py-3 text-right font-medium">수량</th>
                <th className="px-4 py-3 text-right font-medium">단가</th>
                <th className="px-4 py-3 text-right font-medium">소계</th>
              </tr>
            </thead>
            <tbody>
              {(order.items ?? []).map((item) => (
                <tr key={item.id} className="border-b last:border-0">
                  <td className="px-4 py-2.5">{item.item_name}</td>
                  <td className="px-4 py-2.5 text-right">{item.quantity} {item.unit}</td>
                  <td className="px-4 py-2.5 text-right">{item.unit_price.toLocaleString()}원</td>
                  <td className="px-4 py-2.5 text-right font-medium">{item.subtotal.toLocaleString()}원</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2">
        {order.status === "draft" && (
          <>
            <button
              onClick={() => setShowCancelModal(true)}
              className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              취소
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitPO.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              OPS 승인 요청
            </button>
          </>
        )}
        {order.status === "submitted" && (
          <button
            onClick={handleApprove}
            disabled={approvePO.isPending}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            발주 승인 (OPS)
          </button>
        )}
      </div>

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-xl bg-card p-6 shadow-xl w-80">
            <h3 className="mb-3 font-semibold">발주 취소</h3>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="취소 사유를 입력하세요 (필수)"
              rows={3}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => setShowCancelModal(false)}
                className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              >
                닫기
              </button>
              <button
                onClick={handleCancel}
                disabled={!cancelReason.trim() || cancelPO.isPending}
                className="rounded-md bg-destructive px-3 py-1.5 text-sm text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
              >
                취소 확정
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
