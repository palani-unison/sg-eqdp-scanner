"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

export type MarketRow = {
  date: string;
  cum: number; // cumulative log return from start
};

type Props = {
  data: MarketRow[];
  events: { date: string; label: string }[];
};

const FMT_PCT = (x: number) => `${(x * 100).toFixed(1)}%`;

export function MarketChart({ data, events }: Props) {
  if (!data?.length) {
    return (
      <div className="rounded border border-ink/10 p-6 text-ink-mid text-sm">
        No market data — run <code>pipelines/compute_metrics.py</code>.
      </div>
    );
  }
  // Sparse x-axis ticks: every ~120 trading days
  const ticks: string[] = [];
  const step = Math.max(1, Math.floor(data.length / 6));
  for (let i = 0; i < data.length; i += step) ticks.push(data[i].date);
  if (ticks[ticks.length - 1] !== data[data.length - 1].date) {
    ticks.push(data[data.length - 1].date);
  }

  const eventDates = new Set(data.map((r) => r.date));

  return (
    <div className="w-full h-80">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 12, bottom: 10, left: 8 }}>
          <defs>
            <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1f6feb" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#1f6feb" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            ticks={ticks}
            stroke="#404040"
            fontSize={11}
          />
          <YAxis
            tickFormatter={FMT_PCT}
            stroke="#404040"
            fontSize={11}
            width={62}
          />
          <ReferenceLine y={0} stroke="#0a0a0a" strokeDasharray="2 2" />
          {events
            .filter((e) => eventDates.has(e.date))
            .map((e) => (
              <ReferenceLine
                key={e.date}
                x={e.date}
                stroke="#b45309"
                strokeWidth={1.5}
                label={{
                  value: e.label,
                  position: "insideTopRight",
                  fontSize: 10,
                  fill: "#b45309",
                }}
              />
            ))}
          <Tooltip
            formatter={(v) => {
              const n = typeof v === "number" ? v : Number(v);
              return Number.isFinite(n) ? FMT_PCT(n as number) : "—";
            }}
            contentStyle={{ fontSize: 11 }}
          />
          <Area
            type="monotone"
            dataKey="cum"
            stroke="#1f6feb"
            strokeWidth={2}
            fill="url(#fill)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
