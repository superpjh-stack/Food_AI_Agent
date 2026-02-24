"use client";

import { LEGAL_ALLERGENS } from "@/lib/utils/allergen";
import { cn } from "@/lib/utils/cn";

interface AllergenBadgeProps {
  allergens: string[];
  format?: "number" | "text" | "compact";
  className?: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  "난류": "bg-yellow-100 text-yellow-800",
  "우유": "bg-blue-100 text-blue-800",
  "땅콩": "bg-red-100 text-red-800",
  "밀": "bg-amber-100 text-amber-800",
  "새우": "bg-orange-100 text-orange-800",
  "게": "bg-orange-100 text-orange-800",
};

export function AllergenBadge({ allergens, format = "compact", className }: AllergenBadgeProps) {
  if (!allergens.length) return null;

  const sorted = allergens
    .map((name) => ({ name, num: LEGAL_ALLERGENS[name] }))
    .filter((a) => a.num !== undefined)
    .sort((a, b) => (a.num ?? 0) - (b.num ?? 0));

  if (format === "number") {
    return (
      <span className={cn("text-xs text-muted-foreground", className)}>
        {sorted.map((a) => a.num).join(".")}
      </span>
    );
  }

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {sorted.map((a) => (
        <span
          key={a.name}
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            SEVERITY_COLORS[a.name] ?? "bg-gray-100 text-gray-800"
          )}
          title={a.name}
        >
          {format === "compact" ? a.num : `${a.name}(${a.num})`}
        </span>
      ))}
    </div>
  );
}

export function AllergenNeedsVerification({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-1">
      {items.map((item) => (
        <span
          key={item}
          className="inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-700"
        >
          {item} - 확인 필요
        </span>
      ))}
    </div>
  );
}
