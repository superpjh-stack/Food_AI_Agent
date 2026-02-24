"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

interface ForecastDataPoint {
  date: string;
  predicted_mid?: number;
  predicted_min?: number;
  predicted_max?: number;
  actual?: number;
}

interface ForecastChartProps {
  data: ForecastDataPoint[];
}

export function ForecastChart({ data }: ForecastChartProps) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="predicted_mid"
            name="예측 (중앙)"
            stroke="#6366f1"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="predicted_min"
            name="예측 (최소)"
            stroke="#a5b4fc"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="predicted_max"
            name="예측 (최대)"
            stroke="#a5b4fc"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="actual"
            name="실제 식수"
            stroke="#10b981"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
