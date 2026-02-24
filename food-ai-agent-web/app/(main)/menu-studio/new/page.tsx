"use client";

import { useRouter } from "next/navigation";
import { MenuGenerationForm } from "@/components/menu/menu-generation-form";
import type { MenuGenerationParams } from "@/components/menu/menu-generation-form";
import { useGenerateMenuPlan } from "@/lib/hooks/use-menu-plans";

export default function NewMenuPlanPage() {
  const router = useRouter();
  const generateMutation = useGenerateMenuPlan();

  const handleSubmit = async (params: MenuGenerationParams) => {
    try {
      const result = await generateMutation.mutateAsync(params);
      if (result?.id) {
        router.push(`/menu-studio/${result.id}`);
      }
    } catch {
      // Error is handled by TanStack Query
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Generate New Menu Plan</h1>
        <p className="text-sm text-muted-foreground">
          Configure parameters and let AI generate an optimized menu plan.
        </p>
      </div>

      {generateMutation.isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to generate menu plan. Please try again.
        </div>
      )}

      <MenuGenerationForm
        onSubmit={handleSubmit}
        isLoading={generateMutation.isPending}
      />
    </div>
  );
}
