"use client";

import { useState } from "react";

interface ScaledIngredient {
  name: string;
  amount: number;
  unit: string;
}

interface RecipeScalerProps {
  recipeId: string;
  baseName: string;
  baseServings: number;
  onScale: (params: { recipeId: string; targetServings: number }) => void;
  scaledResult?: {
    target_servings: number;
    scaled_ingredients: ScaledIngredient[];
    seasoning_notes: string;
  } | null;
  isLoading: boolean;
}

export function RecipeScaler({
  baseName,
  baseServings,
  recipeId,
  onScale,
  scaledResult,
  isLoading,
}: RecipeScalerProps) {
  const [targetServings, setTargetServings] = useState(baseServings);

  const handleScale = () => {
    onScale({ recipeId, targetServings });
  };

  return (
    <div className="rounded-lg border p-4">
      <h3 className="mb-3 text-sm font-semibold">Recipe Scaler</h3>
      <p className="mb-3 text-xs text-muted-foreground">
        {baseName} - Base: {baseServings} servings
      </p>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="block text-sm font-medium">Target Servings</label>
          <input
            type="number"
            value={targetServings}
            onChange={(e) => setTargetServings(Number(e.target.value))}
            className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
            min={1}
          />
        </div>
        <button
          onClick={handleScale}
          disabled={isLoading || targetServings < 1}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? "Scaling..." : "Scale"}
        </button>
      </div>

      {scaledResult && (
        <div className="mt-4 space-y-3">
          <h4 className="text-sm font-medium">
            Scaled for {scaledResult.target_servings} servings
          </h4>

          <div className="rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-3 py-2 text-left font-medium">Ingredient</th>
                  <th className="px-3 py-2 text-right font-medium">Amount</th>
                  <th className="px-3 py-2 text-left font-medium">Unit</th>
                </tr>
              </thead>
              <tbody>
                {scaledResult.scaled_ingredients.map((ing, idx) => (
                  <tr key={idx} className="border-b last:border-0">
                    <td className="px-3 py-2">{ing.name}</td>
                    <td className="px-3 py-2 text-right">{ing.amount.toFixed(1)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{ing.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {scaledResult.seasoning_notes && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <h5 className="text-xs font-medium text-amber-800">Seasoning Notes</h5>
              <p className="mt-1 text-xs text-amber-700">{scaledResult.seasoning_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
