"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SETTINGS_TABS = [
  { href: "/settings/sites", label: "Sites", description: "Manage facility sites" },
  { href: "/settings/items", label: "Food Items", description: "Food item master data" },
  { href: "/settings/policies", label: "Policies", description: "Nutrition & allergen policies" },
  { href: "/settings/users", label: "Users", description: "User management (ADM)" },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">
          System configuration and master data management
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SETTINGS_TABS.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className="rounded-lg border bg-card p-5 hover:bg-muted/50 transition-colors"
          >
            <h2 className="font-semibold">{tab.label}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{tab.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
