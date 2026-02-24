"use client";

import { useEffect, useState } from "react";
import { http } from "@/lib/http";

interface Item {
  id: string;
  name: string;
  category: string;
  sub_category: string | null;
  unit: string;
  allergens: string[];
  storage_condition: string | null;
  is_active: boolean;
}

const CATEGORIES = ["전체", "육류", "수산", "채소", "양념", "유제품", "곡류", "기타"];

export default function ItemsSettingsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const perPage = 20;

  const fetchItems = async (pg: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(pg), per_page: String(perPage) });
      if (category) params.set("category", category);
      if (search) params.set("search", search);

      const res = await http<{ data: Item[]; meta: { total: number } }>(`/items?${params}`);
      const list: Item[] = Array.isArray(res) ? res : (res as { data: Item[] }).data ?? [];
      const meta = Array.isArray(res) ? { total: list.length } : (res as { meta: { total: number } }).meta;
      setItems(list);
      setTotal(meta?.total ?? list.length);
      setPage(pg);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load items");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchItems(1);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Food Items</h1>
        <p className="text-sm text-muted-foreground">Master data for food ingredients</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat === "전체" ? "" : cat)}
              className={`rounded-full px-3 py-1 text-sm transition-colors ${
                (cat === "전체" && !category) || category === cat
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted hover:bg-muted/80"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <form onSubmit={handleSearch} className="ml-auto flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search items..."
            className="rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            type="submit"
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
          >
            Search
          </button>
        </form>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          Loading items...
        </div>
      ) : (
        <>
          <div className="rounded-lg border">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/40">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Name</th>
                  <th className="px-4 py-3 text-left font-medium">Category</th>
                  <th className="px-4 py-3 text-left font-medium">Unit</th>
                  <th className="px-4 py-3 text-left font-medium">Storage</th>
                  <th className="px-4 py-3 text-left font-medium">Allergens</th>
                  <th className="px-4 py-3 text-center font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                      No items found
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.id} className="hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">{item.name}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {item.category}
                        {item.sub_category ? ` / ${item.sub_category}` : ""}
                      </td>
                      <td className="px-4 py-3">{item.unit}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {item.storage_condition ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {(item.allergens ?? []).map((a) => (
                            <span
                              key={a}
                              className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800"
                            >
                              {a}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            item.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {item.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > perPage && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                {(page - 1) * perPage + 1}–{Math.min(page * perPage, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => fetchItems(page - 1)}
                  className="rounded-md border px-3 py-1 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={page * perPage >= total}
                  onClick={() => fetchItems(page + 1)}
                  className="rounded-md border px-3 py-1 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
