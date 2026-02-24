"use client";

import Link from "next/link";
import { useMenuPlans } from "@/lib/hooks/use-menu-plans";
import { MenuPlanTable } from "@/components/menu/menu-plan-table";

export default function MenuStudioPage() {
  const { data, isLoading } = useMenuPlans();
  const plans = (data as unknown as { data: typeof import("@/types").MenuPlan[] })?.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Menu Studio</h1>
          <p className="text-sm text-muted-foreground">
            AI-powered menu planning and nutrition management
          </p>
        </div>
        <Link
          href="/menu-studio/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          + New Menu Plan
        </Link>
      </div>

      <MenuPlanTable plans={plans} isLoading={isLoading} />
    </div>
  );
}
