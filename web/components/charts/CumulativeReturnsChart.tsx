"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
} from "recharts";

export type CohortRow = {
  date: string;
  treatment: number | null;
  control: number | null;
  sti: number | null;
};

type Props = {
  data: CohortRow[];
  events: { date: string; label: string }[];
};

const FMT_PCT = (x: number | null) =>
  x === null || x === undefined ? "—" : `${(x * 100).toFixed(1)}%`;

export function CumulativeReturnsChart({ data, events }: Props) {
  if (!data?.length) {
    return (
      <div className="border border-line p-6 text-ink-mid text-sm">
        No cohort data — run <code>pipelines/compute_summaries.py</code>.
      </div>
    );
  }
  const ticks: string[] = [];
  const step = Math.max(1, Math.floor(data.length / 6));
  for (let i = 0; i < data.length; i += step) ticks.push(data[i].date);
  if (ticks[ticks.length - 1] !== data[data.length - 1].date) {
    ticks.push(data[data.length - 1].date);
  }
  const dateSet = new Set(data.map((r) => r.date));

  return (
    <div className="w-full h-96">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 10, right: 24, bottom: 5, left: 12 }}>
          <CartesianGrid stroke="#e6e4dd" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            ticks={ticks}
            stroke="#525866"
            fontSize={11}
          />
          <YAxis
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            stroke="#525866"
            fontSize={11}
            width={56}
          />
          <ReferenceLine y={0} stroke="#0b1f3a" strokeDasharray="2 2" />
          {events
            .filter((e) => dateSet.has(e.date))
            .map((e) => (
              <ReferenceLine
                key={e.date}
                x={e.date}
                stroke="#a36410"
                strokeDasharray="4 3"
                label={{
                  value: e.label,
                  position: "insideTopRight",
                  fontSize: 10,
                  fill: "#a36410",
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
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="treatment"
            name="Treatment cohort (T1/T2/T3)"
            stroke="#2251ff"
            strokeWidth={2.2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="control"
            name="Control cohort (STI-30)"
            stroke="#0e7a3e"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="sti"
            name="STI Index"
            stroke="#525866"
            strokeWidth={1.5}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
