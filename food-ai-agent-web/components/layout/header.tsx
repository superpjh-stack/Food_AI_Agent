"use client";

import { useState, useRef, useEffect } from "react";
import { useAlerts } from "@/lib/hooks/use-dashboard";
import { SiteSelector } from "@/components/layout/site-selector";

export function Header() {
  const { data: alerts } = useAlerts();
  const [showAlerts, setShowAlerts] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const alertCount = alerts?.length ?? 0;

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowAlerts(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6 print:hidden">
      <div className="flex items-center gap-4">
        <SiteSelector />
      </div>
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div ref={dropdownRef} className="relative">
          <button
            onClick={() => setShowAlerts(!showAlerts)}
            className="relative rounded-md p-2 text-muted-foreground hover:bg-muted"
          >
            <span className="sr-only">Notifications</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            {alertCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                {alertCount}
              </span>
            )}
          </button>

          {/* Dropdown */}
          {showAlerts && (
            <div className="absolute right-0 top-full z-50 mt-1 w-80 rounded-lg border bg-card p-2 shadow-lg">
              <h3 className="px-2 py-1 text-sm font-semibold">Notifications</h3>
              {!alerts || alerts.length === 0 ? (
                <p className="px-2 py-3 text-sm text-muted-foreground">No active alerts</p>
              ) : (
                <div className="space-y-1">
                  {alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`flex items-center gap-2 rounded-md p-2 text-sm ${
                        alert.severity === "danger"
                          ? "bg-red-50 text-red-700"
                          : alert.severity === "warning"
                            ? "bg-amber-50 text-amber-700"
                            : "bg-blue-50 text-blue-700"
                      }`}
                    >
                      <span className="flex-1">{alert.message}</span>
                      <span className="shrink-0 font-bold">{alert.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="text-sm font-medium text-foreground">User</div>
      </div>
    </header>
  );
}
