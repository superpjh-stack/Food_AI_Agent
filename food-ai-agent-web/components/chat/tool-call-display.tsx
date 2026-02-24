"use client";

interface ToolCallDisplayProps {
  name: string;
  status: string;
  data?: unknown;
}

const TOOL_LABELS: Record<string, string> = {
  generate_menu_plan: "Generating menu plan",
  validate_nutrition: "Validating nutrition",
  tag_allergens: "Tagging allergens",
  check_diversity: "Checking diversity",
  search_recipes: "Searching recipes",
  scale_recipe: "Scaling recipe",
  generate_haccp_checklist: "Generating HACCP checklist",
  check_haccp_completion: "Checking HACCP completion",
  generate_audit_report: "Generating audit report",
  query_dashboard: "Querying dashboard",
};

export function ToolCallDisplay({ name, status }: ToolCallDisplayProps) {
  const label = TOOL_LABELS[name] ?? name;

  return (
    <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-1.5 text-xs">
      {status === "started" && (
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
      )}
      {status === "completed" && (
        <span className="text-green-500">{"\u2713"}</span>
      )}
      {status === "error" && (
        <span className="text-red-500">{"\u2717"}</span>
      )}
      <span>{label}</span>
    </div>
  );
}
