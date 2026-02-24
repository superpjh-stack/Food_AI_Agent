"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

interface WasteTrendDataPoint {
  date: string;
  avg_waste_pct: number;
}

interface WasteTrendChartProps {
  data: WasteTrendDataPoint[];
  targetPct?: number;
}

export function WasteTrendChart({ data, targetPct = 10 }: WasteTrendChartProps) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis
            tickFormatter={(v) => `${v}%`}
            domain={[0, 50]}
            tick={{ fontSize: 11 }}
          />
          <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`, "잔반률"]} />
          <ReferenceLine y={targetPct} stroke="#ef4444" strokeDasharray="5 5" label={{ value: "목표", fontSize: 11 }} />
          <Bar
            dataKey="avg_waste_pct"
            name="평균 잔반률"
            fill="#f59e0b"
            radius={[2, 2, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
