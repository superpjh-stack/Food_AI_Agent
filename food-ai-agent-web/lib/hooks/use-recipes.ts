"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http } from "@/lib/http";
import type { Recipe, PaginatedResponse } from "@/types";

interface ListParams {
  page?: number;
  per_page?: number;
  category?: string;
  search?: string;
}

export function useRecipes(params: ListParams = {}) {
  const { page = 1, per_page = 20, category, search } = params;

  return useQuery({
    queryKey: ["recipes", page, per_page, category, search],
    queryFn: async () => {
      const qs = new URLSearchParams({ page: String(page), per_page: String(per_page) });
      if (category) qs.set("category", category);
      if (search) qs.set("search", search);
      const res = await http<PaginatedResponse<Recipe>>(`/recipes?${qs}`);
      return res as unknown as PaginatedResponse<Recipe>;
    },
  });
}

export function useRecipe(recipeId: string | undefined) {
  return useQuery({
    queryKey: ["recipe", recipeId],
    queryFn: () => http<Recipe>(`/recipes/${recipeId}`),
    enabled: !!recipeId,
  });
}

export function useSearchRecipes() {
  return useMutation({
    mutationFn: (params: {
      query: string;
      category?: string;
      allergen_exclude?: string[];
      max_results?: number;
    }) =>
      http<Recipe[]>("/recipes/search", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  });
}

export function useScaleRecipe() {
  return useMutation({
    mutationFn: ({ recipeId, targetServings }: { recipeId: string; targetServings: number }) =>
      http<{
        recipe_id: string;
        original_servings: number;
        target_servings: number;
        scaled_ingredients: { name: string; amount: number; unit: string }[];
        seasoning_notes: string;
      }>(`/recipes/${recipeId}/scale`, {
        method: "POST",
        body: JSON.stringify({ target_servings: targetServings }),
      }),
  });
}

export function useCreateRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<Recipe>) =>
      http<Recipe>("/recipes", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
}
