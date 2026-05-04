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

export type EventStudyRow = {
  t: number;
  treated: number | null;
  control: number | null;
};

type Props = {
  eventLabel: string;
  data: EventStudyRow[];
};

const FMT_PCT = (x: number | null) =>
  x === null || x === undefined ? "—" : `${(x * 100).toFixed(2)}%`;

export function EventStudyChart({ eventLabel, data }: Props) {
  if (!data?.length) {
    return (
      <div className="rounded border border-ink/10 p-4 text-ink-mid text-xs">
        No event-study data for {eventLabel}.
      </div>
    );
  }

  return (
    <div className="w-full">
      <p className="text-sm font-medium text-ink mb-2">{eventLabel}</p>
      <div className="w-full h-56">
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 5, right: 12, bottom: 5, left: 8 }}
          >
            <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              ticks={uniqueTicks(data)}
              stroke="#404040"
              fontSize={11}
              label={{ value: "trading day t", position: "insideBottom", offset: -2, fontSize: 11, fill: "#737373" }}
            />
            <YAxis
              tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              stroke="#404040"
              fontSize={11}
              width={58}
            />
            <ReferenceLine y={0} stroke="#a3a3a3" strokeDasharray="2 2" />
            <ReferenceLine x={0} stroke="#0a0a0a" strokeDasharray="3 3" label={{ value: "event", position: "insideTopRight", fontSize: 10, fill: "#404040" }} />
            <Tooltip
              formatter={(v) => {
                const n = typeof v === "number" ? v : v == null ? null : Number(v);
                return FMT_PCT(Number.isFinite(n) ? (n as number) : null);
              }}
              contentStyle={{ fontSize: 11 }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="treated"
              name="Treated mean CAR"
              stroke="#1f6feb"
              strokeWidth={2}
              dot={{ r: 2 }}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="control"
              name="Control mean CAR"
              stroke="#737373"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={{ r: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function uniqueTicks(data: EventStudyRow[]): number[] {
  const ts = data.map((d) => d.t);
  const lo = Math.min(...ts);
  const hi = Math.max(...ts);
  const step = Math.max(1, Math.ceil((hi - lo) / 6));
  const out: number[] = [];
  for (let v = lo; v <= hi; v += step) out.push(v);
  if (!out.includes(0) && lo <= 0 && hi >= 0) out.push(0);
  return out.sort((a, b) => a - b);
}
