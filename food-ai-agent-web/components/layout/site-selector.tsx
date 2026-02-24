"use client";

import { useEffect, useRef, useState } from "react";
import { useSiteStore } from "@/lib/stores/site-store";
import { http } from "@/lib/http";

interface Site {
  id: string;
  name: string;
  type: string;
  capacity: number;
}

interface SiteListResponse {
  data: Site[];
  meta: { page: number; per_page: number; total: number };
}

export function SiteSelector() {
  const { sites, currentSite, setSites, setCurrentSite } = useSiteStore();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch sites on mount if not already loaded
  useEffect(() => {
    if (sites.length > 0) return;

    setLoading(true);
    http<SiteListResponse>("/sites?is_active=true&per_page=100")
      .then((res) => {
        // http() returns json.data, so res here is the raw response data field
        // The server returns { success, data: [], meta: {} }
        // http() strips the wrapper and returns json.data which is { data: [], meta: {} }
        // Actually http() returns json.data = the array since our sites endpoint nests differently.
        // Let's handle both shapes gracefully.
        const list: Site[] = Array.isArray(res) ? res : (res as SiteListResponse).data ?? [];
        setSites(list);
        if (list.length > 0 && !currentSite) {
          setCurrentSite(list[0]);
        }
      })
      .catch(() => {
        // silently fail — user will see placeholder
      })
      .finally(() => setLoading(false));
  }, [sites.length, currentSite, setSites, setCurrentSite]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (site: Site) => {
    setCurrentSite(site);
    setOpen(false);
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        disabled={loading}
        className="flex items-center gap-2 rounded-md border bg-background px-3 py-1.5 text-sm font-medium hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {/* Building icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-muted-foreground"
          aria-hidden="true"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
        <span className="max-w-[160px] truncate">
          {loading ? "Loading..." : (currentSite?.name ?? "Select Site")}
        </span>
        {/* Chevron */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && sites.length > 0 && (
        <div
          role="listbox"
          aria-label="Site list"
          className="absolute left-0 top-full z-50 mt-1 min-w-[200px] rounded-lg border bg-card p-1 shadow-lg"
        >
          {sites.map((site) => (
            <button
              key={site.id}
              role="option"
              aria-selected={site.id === currentSite?.id}
              onClick={() => handleSelect(site)}
              className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted ${
                site.id === currentSite?.id
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-foreground"
              }`}
            >
              <span className="flex-1 truncate">{site.name}</span>
              <span className="shrink-0 text-xs text-muted-foreground capitalize">{site.type}</span>
              {site.id === currentSite?.id && (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="shrink-0 text-primary"
                  aria-hidden="true"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}

      {open && !loading && sites.length === 0 && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[200px] rounded-lg border bg-card px-3 py-2 shadow-lg text-sm text-muted-foreground">
          No sites available
        </div>
      )}
    </div>
  );
}
