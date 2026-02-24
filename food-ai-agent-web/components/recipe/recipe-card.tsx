"use client";

import Link from "next/link";
import { AllergenBadge } from "@/components/menu/allergen-badge";
import type { Recipe } from "@/types";

interface RecipeCardProps {
  recipe: Recipe;
}

const DIFFICULTY_LABEL: Record<string, { text: string; color: string }> = {
  easy: { text: "Easy", color: "text-green-600" },
  medium: { text: "Medium", color: "text-amber-600" },
  hard: { text: "Hard", color: "text-red-600" },
};

export function RecipeCard({ recipe }: RecipeCardProps) {
  const difficulty = recipe.difficulty ? DIFFICULTY_LABEL[recipe.difficulty] : null;
  const totalTime = (recipe.prep_time_min ?? 0) + (recipe.cook_time_min ?? 0);

  return (
    <Link
      href={`/recipes/${recipe.id}`}
      className="block rounded-lg border p-4 transition-colors hover:bg-muted/30"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="font-medium">{recipe.name}</h3>
        {difficulty && (
          <span className={`text-xs font-medium ${difficulty.color}`}>
            {difficulty.text}
          </span>
        )}
      </div>

      <div className="mb-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
        {recipe.category && <span>{recipe.category}</span>}
        {recipe.sub_category && (
          <>
            <span>/</span>
            <span>{recipe.sub_category}</span>
          </>
        )}
        {totalTime > 0 && <span>{totalTime}min</span>}
        <span>{recipe.servings_base} servings</span>
      </div>

      {recipe.allergens.length > 0 && (
        <AllergenBadge allergens={recipe.allergens} format="compact" />
      )}

      {recipe.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {recipe.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}
