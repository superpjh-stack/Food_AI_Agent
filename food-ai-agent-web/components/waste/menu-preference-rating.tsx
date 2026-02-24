"use client";

import type { MenuPreference } from "@/lib/hooks/use-waste";

interface MenuPreferenceRatingProps {
  preferences: MenuPreference[];
}

function ScoreBar({ score }: { score: number }) {
  // score: -1.0 to 1.0
  const pct = Math.round(((score + 1) / 2) * 100);
  const colorClass =
    score >= 0.3
      ? "bg-green-500"
      : score >= -0.3
      ? "bg-yellow-400"
      : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 rounded-full bg-gray-200">
        <div
          className={`h-2 rounded-full ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground">{score.toFixed(2)}</span>
    </div>
  );
}

export function MenuPreferenceRating({ preferences }: MenuPreferenceRatingProps) {
  const sorted = [...preferences].sort((a, b) => b.preference_score - a.preference_score);
  const top5 = sorted.slice(0, 5);
  const bottom5 = sorted.slice(-5).reverse();

  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h4 className="mb-2 text-xs font-semibold text-green-700">선호도 상위 5</h4>
        <ul className="space-y-2">
          {top5.map((p) => (
            <li key={p.id} className="text-xs">
              <div className="truncate font-medium">{p.recipe_id.slice(0, 8)}...</div>
              <ScoreBar score={p.preference_score} />
              <div className="text-muted-foreground">잔반률 avg: {p.waste_avg_pct.toFixed(1)}%</div>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h4 className="mb-2 text-xs font-semibold text-red-700">선호도 하위 5</h4>
        <ul className="space-y-2">
          {bottom5.map((p) => (
            <li key={p.id} className="text-xs">
              <div className="truncate font-medium">{p.recipe_id.slice(0, 8)}...</div>
              <ScoreBar score={p.preference_score} />
              <div className="text-muted-foreground">잔반률 avg: {p.waste_avg_pct.toFixed(1)}%</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
