"use client";

const CATEGORY_COLORS: Record<string, string> = {
  "맛/품질": "bg-orange-100 text-orange-800",
  "이물": "bg-red-100 text-red-800",
  "양/분량": "bg-blue-100 text-blue-800",
  "온도": "bg-cyan-100 text-cyan-800",
  "알레르겐": "bg-purple-100 text-purple-800",
  "위생/HACCP": "bg-rose-100 text-rose-800",
  "서비스": "bg-green-100 text-green-800",
  "기타": "bg-gray-100 text-gray-800",
};

interface ClaimCategoryBadgeProps {
  category: string;
}

export function ClaimCategoryBadge({ category }: ClaimCategoryBadgeProps) {
  const colorClass = CATEGORY_COLORS[category] ?? "bg-gray-100 text-gray-800";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {category}
    </span>
  );
}
