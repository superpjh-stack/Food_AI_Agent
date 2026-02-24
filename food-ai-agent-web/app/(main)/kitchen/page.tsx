"use client";

import { useState } from "react";
import { useWorkOrders, useUpdateWorkOrderStatus } from "@/lib/hooks/use-work-orders";
import { WorkOrderCard } from "@/components/kitchen/work-order-card";
import { WorkOrderChecklist } from "@/components/kitchen/work-order-checklist";
import type { WorkOrder } from "@/types";

export default function KitchenPage() {
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const { data, isLoading } = useWorkOrders({ date: selectedDate });
  const statusMutation = useUpdateWorkOrderStatus();

  const orders = (data as unknown as { data: WorkOrder[] })?.data ?? [];

  const handleStatusChange = async (orderId: string, status: string) => {
    await statusMutation.mutateAsync({ orderId, status });
    setSelectedOrder(null);
  };

  const pendingOrders = orders.filter((o) => o.status === "pending");
  const inProgressOrders = orders.filter((o) => o.status === "in_progress");
  const completedOrders = orders.filter((o) => o.status === "completed");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Kitchen Mode</h1>
          <p className="text-sm text-muted-foreground">
            Work orders and cooking checklists for today
          </p>
        </div>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => {
            setSelectedDate(e.target.value);
            setSelectedOrder(null);
          }}
          className="rounded-md border bg-background px-3 py-2 text-sm"
        />
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          Loading work orders...
        </div>
      ) : orders.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          No work orders for {selectedDate}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Order list */}
          <div className="space-y-4 lg:col-span-1">
            {pendingOrders.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
                  Pending ({pendingOrders.length})
                </h3>
                <div className="space-y-2">
                  {pendingOrders.map((o) => (
                    <WorkOrderCard
                      key={o.id}
                      order={o}
                      onSelect={setSelectedOrder}
                      isSelected={selectedOrder?.id === o.id}
                    />
                  ))}
                </div>
              </div>
            )}
            {inProgressOrders.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-blue-600">
                  In Progress ({inProgressOrders.length})
                </h3>
                <div className="space-y-2">
                  {inProgressOrders.map((o) => (
                    <WorkOrderCard
                      key={o.id}
                      order={o}
                      onSelect={setSelectedOrder}
                      isSelected={selectedOrder?.id === o.id}
                    />
                  ))}
                </div>
              </div>
            )}
            {completedOrders.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-green-600">
                  Completed ({completedOrders.length})
                </h3>
                <div className="space-y-2">
                  {completedOrders.map((o) => (
                    <WorkOrderCard
                      key={o.id}
                      order={o}
                      onSelect={setSelectedOrder}
                      isSelected={selectedOrder?.id === o.id}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Selected order detail */}
          <div className="lg:col-span-2">
            {selectedOrder ? (
              <WorkOrderChecklist
                order={selectedOrder}
                onStart={() => handleStatusChange(selectedOrder.id, "in_progress")}
                onComplete={() => handleStatusChange(selectedOrder.id, "completed")}
              />
            ) : (
              <div className="flex h-60 items-center justify-center rounded-lg border text-muted-foreground">
                Select a work order to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
