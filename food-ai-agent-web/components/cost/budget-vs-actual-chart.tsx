"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

interface BudgetVsActualPoint {
  label: string;
  target: number;
  estimated: number;
  actual?: number;
}

interface BudgetVsActualChartProps {
  data: BudgetVsActualPoint[];
}

export function BudgetVsActualChart({ data }: BudgetVsActualChartProps) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number) => [`${v.toLocaleString()}원`]} />
          <Legend />
          <Bar dataKey="target" name="목표 원가" fill="#6366f1" />
          <Bar dataKey="estimated" name="예상 원가" fill="#f59e0b" />
          <Bar dataKey="actual" name="실발주 원가" fill="#10b981" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
