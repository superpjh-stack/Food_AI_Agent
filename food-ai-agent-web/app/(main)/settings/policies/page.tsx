"use client";

import { useEffect, useState } from "react";
import { http } from "@/lib/http";

interface NutritionPolicy {
  id: string;
  site_id: string | null;
  name: string;
  meal_type: string | null;
  criteria: Record<string, { min?: number; max?: number }>;
  is_active: boolean;
}

interface AllergenPolicy {
  id: string;
  site_id: string | null;
  name: string;
  legal_allergens: string[];
  custom_allergens: string[];
  display_format: string;
  is_active: boolean;
}

type TabKey = "nutrition" | "allergen";

export default function PoliciesSettingsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("nutrition");
  const [nutritionPolicies, setNutritionPolicies] = useState<NutritionPolicy[]>([]);
  const [allergenPolicies, setAllergenPolicies] = useState<AllergenPolicy[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "nutrition") {
        const res = await http<{ data: NutritionPolicy[] }>("/policies/nutrition?per_page=50");
        const list = Array.isArray(res) ? res : (res as { data: NutritionPolicy[] }).data ?? [];
        setNutritionPolicies(list);
      } else {
        const res = await http<{ data: AllergenPolicy[] }>("/policies/allergen?per_page=50");
        const list = Array.isArray(res) ? res : (res as { data: AllergenPolicy[] }).data ?? [];
        setAllergenPolicies(list);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load policies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Policies</h1>
        <p className="text-sm text-muted-foreground">
          Configure nutrition targets and allergen disclosure rules
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b">
        {(["nutrition", "allergen"] as TabKey[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab === "nutrition" ? "Nutrition Policies" : "Allergen Policies"}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          Loading policies...
        </div>
      ) : activeTab === "nutrition" ? (
        <div className="space-y-3">
          {nutritionPolicies.length === 0 ? (
            <div className="rounded-lg border py-12 text-center text-muted-foreground">
              No nutrition policies found
            </div>
          ) : (
            nutritionPolicies.map((p) => (
              <div key={p.id} className="rounded-lg border bg-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{p.name}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Meal type: {p.meal_type ?? "all"} &bull;{" "}
                      {p.site_id ? "Site-specific" : "Global default"}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {p.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(p.criteria).map(([key, range]) => (
                    <span
                      key={key}
                      className="rounded bg-muted px-2 py-1 text-xs"
                    >
                      <span className="font-medium">{key}</span>:{" "}
                      {range.min != null ? `${range.min}` : "—"}
                      {" – "}
                      {range.max != null ? `${range.max}` : "—"}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {allergenPolicies.length === 0 ? (
            <div className="rounded-lg border py-12 text-center text-muted-foreground">
              No allergen policies found
            </div>
          ) : (
            allergenPolicies.map((p) => (
              <div key={p.id} className="rounded-lg border bg-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{p.name}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Display: {p.display_format} &bull;{" "}
                      {p.site_id ? "Site-specific" : "Global default"}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {p.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="mt-3">
                  <p className="text-xs text-muted-foreground mb-1">
                    Legal allergens ({p.legal_allergens.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {p.legal_allergens.map((a) => (
                      <span
                        key={a}
                        className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800"
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
