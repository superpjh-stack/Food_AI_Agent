"use client";

interface MenuSwapSuggestion {
  item_name: string;
  current_cost: number;
  suggestion: string;
}

interface MenuSwapSuggestionCardProps {
  suggestion: MenuSwapSuggestion;
}

export function MenuSwapSuggestionCard({ suggestion }: MenuSwapSuggestionCardProps) {
  return (
    <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-sm text-yellow-900">{suggestion.item_name}</div>
          <div className="text-xs text-yellow-700 mt-0.5">{suggestion.suggestion}</div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-xs text-muted-foreground">현재 원가</div>
          <div className="text-sm font-semibold text-yellow-800">
            {suggestion.current_cost.toLocaleString()}원
          </div>
        </div>
      </div>
    </div>
  );
}
