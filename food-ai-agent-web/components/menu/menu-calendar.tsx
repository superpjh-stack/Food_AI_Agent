"use client";

import { AllergenBadge } from "./allergen-badge";
import type { MenuPlanItem } from "@/types";

interface MenuCalendarProps {
  items: MenuPlanItem[];
  periodStart: string;
  periodEnd: string;
}

const COURSE_ORDER = ["rice", "soup", "main", "side1", "side2", "side3", "dessert"];
const COURSE_LABELS: Record<string, string> = {
  rice: "Rice", soup: "Soup", main: "Main", side1: "Side 1",
  side2: "Side 2", side3: "Side 3", dessert: "Dessert",
};

export function MenuCalendar({ items, periodStart, periodEnd }: MenuCalendarProps) {
  // Group items by date
  const byDate = new Map<string, MenuPlanItem[]>();
  for (const item of items) {
    const existing = byDate.get(item.date) ?? [];
    existing.push(item);
    byDate.set(item.date, existing);
  }

  // Generate date range
  const dates: string[] = [];
  const start = new Date(periodStart);
  const end = new Date(periodEnd);
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    dates.push(d.toISOString().split("T")[0]);
  }

  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="border bg-muted/50 px-2 py-2 text-left text-xs font-medium">Course</th>
            {dates.map((d) => {
              const dow = weekdays[new Date(d).getDay()];
              return (
                <th key={d} className="border bg-muted/50 px-2 py-2 text-center text-xs font-medium">
                  <div>{d.slice(5)}</div>
                  <div className="text-muted-foreground">{dow}</div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {COURSE_ORDER.map((course) => (
            <tr key={course}>
              <td className="border bg-muted/30 px-2 py-2 text-xs font-medium">
                {COURSE_LABELS[course] ?? course}
              </td>
              {dates.map((d) => {
                const dayItems = byDate.get(d) ?? [];
                const item = dayItems.find((i) => i.course === course);
                return (
                  <td key={d} className="border px-2 py-2">
                    {item ? (
                      <div>
                        <div className="text-xs font-medium">{item.item_name}</div>
                        {item.allergens.length > 0 && (
                          <AllergenBadge allergens={item.allergens} format="number" className="mt-0.5" />
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
