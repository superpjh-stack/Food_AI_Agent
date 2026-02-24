"use client";

import { useParams } from "next/navigation";
import { useRecipe, useScaleRecipe } from "@/lib/hooks/use-recipes";
import { RecipeDetail } from "@/components/recipe/recipe-detail";
import { RecipeScaler } from "@/components/recipe/recipe-scaler";
import { useState } from "react";

export default function RecipeDetailPage() {
  const params = useParams();
  const recipeId = params.id as string;
  const { data: recipe, isLoading } = useRecipe(recipeId);
  const scaleMutation = useScaleRecipe();
  const [scaleResult, setScaleResult] = useState<{
    target_servings: number;
    scaled_ingredients: { name: string; amount: number; unit: string }[];
    seasoning_notes: string;
  } | null>(null);

  if (isLoading) {
    return (
      <div className="flex h-60 items-center justify-center text-muted-foreground">
        Loading recipe...
      </div>
    );
  }

  if (!recipe) {
    return (
      <div className="flex h-60 items-center justify-center text-muted-foreground">
        Recipe not found.
      </div>
    );
  }

  const handleScale = async (p: { recipeId: string; targetServings: number }) => {
    try {
      const result = await scaleMutation.mutateAsync(p);
      setScaleResult(result);
    } catch {
      // handled by TanStack Query
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <RecipeDetail recipe={recipe} />
      </div>
      <div>
        <RecipeScaler
          recipeId={recipeId}
          baseName={recipe.name}
          baseServings={recipe.servings_base}
          onScale={handleScale}
          scaledResult={scaleResult}
          isLoading={scaleMutation.isPending}
        />
      </div>
    </div>
  );
}
