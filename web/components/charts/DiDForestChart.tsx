"use client";

import {
  ComposedChart,
  Line,
  ErrorBar,
  Scatter,
  ResponsiveContainer,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  LabelList,
} from "recharts";

export type DiDPoint = {
  event: string;
  point: number;
  lower: number;
  upper: number;
  significant: boolean;
};

type Props = {
  data: DiDPoint[];
};

const FMT_PCT = (x: number) => `${(x * 100).toFixed(2)}%`;

export function DiDForestChart({ data }: Props) {
  if (!data?.length) {
    return (
      <div className="rounded border border-ink/10 p-6 text-ink-mid text-sm">
        No bootstrap data yet — run <code>pipelines/compute_bootstrap.py</code>.
      </div>
    );
  }

  // Recharts ErrorBar wants the asymmetric error widths.
  const series = data.map((d) => ({
    event: d.event,
    point: d.point,
    err: [d.point - d.lower, d.upper - d.point] as [number, number],
    significant: d.significant,
  }));

  return (
    <div className="w-full h-80">
      <ResponsiveContainer>
        <ComposedChart
          layout="vertical"
          data={series}
          margin={{ top: 10, right: 40, bottom: 10, left: 40 }}
        >
          <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
          <XAxis
            type="number"
            tickFormatter={FMT_PCT}
            domain={["dataMin", "dataMax"]}
            stroke="#404040"
            fontSize={12}
          />
          <YAxis
            type="category"
            dataKey="event"
            stroke="#404040"
            fontSize={12}
            width={110}
          />
          <ReferenceLine x={0} stroke="#0a0a0a" strokeWidth={1} />
          <Tooltip
            formatter={(value: number | string) =>
              typeof value === "number" ? FMT_PCT(value) : value
            }
            contentStyle={{ fontSize: 12 }}
          />
          <Scatter dataKey="point" fill="#1f6feb" shape="circle">
            <ErrorBar
              dataKey="err"
              direction="x"
              width={4}
              strokeWidth={2}
              stroke="#1f6feb"
            />
            <LabelList
              dataKey="point"
              position="right"
              formatter={(v: number) => FMT_PCT(v)}
              style={{ fontSize: 11, fill: "#404040" }}
            />
          </Scatter>
          {/* Faint line connecting points just to anchor the eye */}
          <Line
            type="linear"
            dataKey="point"
            stroke="transparent"
            isAnimationActive={false}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
