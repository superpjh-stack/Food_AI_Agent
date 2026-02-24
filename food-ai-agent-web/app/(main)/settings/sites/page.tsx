"use client";

import { useEffect, useState } from "react";
import { http } from "@/lib/http";
import { useSiteStore } from "@/lib/stores/site-store";
import { SiteSelector } from "@/components/layout/site-selector";

interface Site {
  id: string;
  name: string;
  type: string;
  capacity: number;
  address: string | null;
  is_active: boolean;
}

export default function SitesSettingsPage() {
  const { sites, setSites } = useSiteStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSites = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await http<{ data: Site[]; meta: object }>("/sites?per_page=100");
      const list: Site[] = Array.isArray(res) ? res : (res as { data: Site[] }).data ?? [];
      setSites(list);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load sites");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sites</h1>
          <p className="text-sm text-muted-foreground">
            Manage facility sites and switch active site
          </p>
        </div>
        <SiteSelector />
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          Loading sites...
        </div>
      ) : (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-right font-medium">Capacity</th>
                <th className="px-4 py-3 text-left font-medium">Address</th>
                <th className="px-4 py-3 text-center font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sites.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    No sites found
                  </td>
                </tr>
              ) : (
                sites.map((site) => (
                  <tr key={site.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3 font-medium">{site.name}</td>
                    <td className="px-4 py-3 capitalize text-muted-foreground">{site.type}</td>
                    <td className="px-4 py-3 text-right">{site.capacity.toLocaleString()}</td>
                    <td className="px-4 py-3 text-muted-foreground">{site.address ?? "—"}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          site.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {site.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
