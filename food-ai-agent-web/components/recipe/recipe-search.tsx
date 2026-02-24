"use client";

import { useState } from "react";

interface RecipeSearchProps {
  onSearch: (params: { query: string; category?: string; allergen_exclude?: string[] }) => void;
  isLoading: boolean;
}

const CATEGORIES = ["한식", "중식", "양식", "일식", "기타"];

export function RecipeSearch({ onSearch, isLoading }: RecipeSearchProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch({
      query,
      category: category || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="flex-1">
        <label className="block text-sm font-medium">Search</label>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="Recipe name or keyword..."
        />
      </div>
      <div className="w-36">
        <label className="block text-sm font-medium">Category</label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="mt-1 block w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="">All</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        disabled={isLoading || !query.trim()}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {isLoading ? "Searching..." : "Search"}
      </button>
    </form>
  );
}
