"use client";

import { AllergenBadge } from "@/components/menu/allergen-badge";
import type { Recipe } from "@/types";

interface RecipeDetailProps {
  recipe: Recipe;
}

export function RecipeDetail({ recipe }: RecipeDetailProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold">{recipe.name}</h2>
        <div className="mt-1 flex flex-wrap gap-3 text-sm text-muted-foreground">
          {recipe.category && <span>{recipe.category}</span>}
          {recipe.sub_category && <span>/ {recipe.sub_category}</span>}
          {recipe.difficulty && <span>Difficulty: {recipe.difficulty}</span>}
          <span>Base: {recipe.servings_base} servings</span>
          {recipe.prep_time_min && <span>Prep: {recipe.prep_time_min}min</span>}
          {recipe.cook_time_min && <span>Cook: {recipe.cook_time_min}min</span>}
        </div>
      </div>

      {/* Allergens */}
      {recipe.allergens.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Allergens</h3>
          <AllergenBadge allergens={recipe.allergens} format="text" />
        </div>
      )}

      {/* Nutrition */}
      {recipe.nutrition_per_serving && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Nutrition (per serving)</h3>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <NutritionStat label="Calories" value={recipe.nutrition_per_serving.kcal} unit="kcal" />
            <NutritionStat label="Protein" value={recipe.nutrition_per_serving.protein} unit="g" />
            <NutritionStat label="Sodium" value={recipe.nutrition_per_serving.sodium} unit="mg" />
            {recipe.nutrition_per_serving.fat !== undefined && (
              <NutritionStat label="Fat" value={recipe.nutrition_per_serving.fat} unit="g" />
            )}
          </div>
        </div>
      )}

      {/* Ingredients */}
      <div>
        <h3 className="mb-2 text-sm font-semibold">
          Ingredients ({recipe.servings_base} servings)
        </h3>
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-3 py-2 text-left font-medium">Name</th>
                <th className="px-3 py-2 text-right font-medium">Amount</th>
                <th className="px-3 py-2 text-left font-medium">Unit</th>
              </tr>
            </thead>
            <tbody>
              {recipe.ingredients.map((ing, idx) => (
                <tr key={idx} className="border-b last:border-0">
                  <td className="px-3 py-2">{ing.name}</td>
                  <td className="px-3 py-2 text-right">{ing.amount}</td>
                  <td className="px-3 py-2 text-muted-foreground">{ing.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Steps */}
      <div>
        <h3 className="mb-2 text-sm font-semibold">Steps</h3>
        <ol className="space-y-3">
          {recipe.steps.map((step) => (
            <li key={step.order} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
                {step.order}
              </span>
              <div className="flex-1">
                <p className="text-sm">{step.description}</p>
                <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                  {step.duration_min && <span>{step.duration_min}min</span>}
                  {step.ccp && (
                    <span className="rounded bg-red-100 px-1.5 py-0.5 font-medium text-red-700">
                      CCP: {step.ccp.type} - {step.ccp.target}
                    </span>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function NutritionStat({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <div className="rounded-lg border p-3 text-center">
      <div className="text-lg font-semibold">{value?.toLocaleString()}</div>
      <div className="text-xs text-muted-foreground">
        {label} ({unit})
      </div>
    </div>
  );
}
