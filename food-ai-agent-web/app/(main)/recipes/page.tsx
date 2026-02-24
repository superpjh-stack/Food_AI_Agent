"use client";

import { useState } from "react";
import { useRecipes, useSearchRecipes } from "@/lib/hooks/use-recipes";
import { RecipeSearch } from "@/components/recipe/recipe-search";
import { RecipeCard } from "@/components/recipe/recipe-card";
import type { Recipe } from "@/types";

export default function RecipesPage() {
  const [searchResults, setSearchResults] = useState<Recipe[] | null>(null);
  const { data, isLoading } = useRecipes();
  const searchMutation = useSearchRecipes();

  const recipes = searchResults ?? (data as unknown as { data: Recipe[] })?.data ?? [];

  const handleSearch = async (params: { query: string; category?: string; allergen_exclude?: string[] }) => {
    try {
      const results = await searchMutation.mutateAsync(params);
      setSearchResults(results);
    } catch {
      // handled by TanStack Query
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Recipe Library</h1>
        <p className="text-sm text-muted-foreground">
          Search and manage recipes with AI-powered hybrid search
        </p>
      </div>

      <RecipeSearch onSearch={handleSearch} isLoading={searchMutation.isPending} />

      {searchResults && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {searchResults.length} results found
          </span>
          <button
            onClick={() => setSearchResults(null)}
            className="text-sm text-primary hover:underline"
          >
            Clear search
          </button>
        </div>
      )}

      {isLoading && !searchResults ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          Loading recipes...
        </div>
      ) : recipes.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          No recipes found.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {recipes.map((recipe) => (
            <RecipeCard key={recipe.id} recipe={recipe} />
          ))}
        </div>
      )}
    </div>
  );
}
