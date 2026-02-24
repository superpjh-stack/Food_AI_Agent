"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "LayoutDashboard" },
  { href: "/menu-studio", label: "Menu Studio", icon: "CalendarDays" },
  { href: "/recipes", label: "Recipes", icon: "ChefHat" },
  { href: "/kitchen", label: "Kitchen", icon: "Flame" },
  { href: "/haccp", label: "HACCP", icon: "ShieldCheck" },
  { href: "/purchase", label: "BOM & 발주", icon: "ShoppingCart" },
  { href: "/inventory", label: "재고/입고", icon: "Package" },
  { href: "/forecast", label: "수요예측", icon: "TrendingUp" },
  { href: "/waste", label: "잔반관리", icon: "Trash2" },
  { href: "/cost-optimizer", label: "원가최적화", icon: "Calculator" },
  { href: "/claims", label: "클레임", icon: "AlertCircle" },
  { href: "/settings", label: "Settings", icon: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 border-r bg-card md:block">
      <div className="flex h-14 items-center border-b px-4">
        <Link href="/dashboard" className="text-lg font-bold text-primary">
          Food AI Agent
        </Link>
      </div>
      <nav className="space-y-1 p-3">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
