"use client";

import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ZAxis,
  Cell,
} from "recharts";

export type ScatterPoint = {
  ticker: string;
  car: number;          // % e.g. 0.32 for 32%
  volumeLift: number;   // % e.g. 0.78 for 78%
  cohort: "treatment" | "control" | "other";
};

type Props = { data: ScatterPoint[] };

const FMT_PCT = (x: number) => `${(x * 100).toFixed(1)}%`;

export function BeneficiaryScatter({ data }: Props) {
  if (!data?.length) {
    return (
      <div className="border border-line p-6 text-ink-mid text-sm">
        No summary data — run <code>pipelines/compute_summaries.py</code>.
      </div>
    );
  }
  const treatment = data.filter((d) => d.cohort === "treatment");
  const control = data.filter((d) => d.cohort === "control");

  return (
    <div className="w-full h-96">
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 10, right: 24, bottom: 25, left: 12 }}>
          <CartesianGrid stroke="#e6e4dd" strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="volumeLift"
            name="Volume lift"
            tickFormatter={FMT_PCT}
            stroke="#525866"
            fontSize={11}
            label={{
              value: "Mean volume lift (post − pre, %)",
              position: "insideBottom",
              offset: -8,
              fontSize: 11,
              fill: "#525866",
            }}
          />
          <YAxis
            type="number"
            dataKey="car"
            name="CAR"
            tickFormatter={FMT_PCT}
            stroke="#525866"
            fontSize={11}
            width={66}
            label={{
              value: "Cumulative AR (sum across 4 events, %)",
              angle: -90,
              position: "insideLeft",
              offset: 8,
              fontSize: 11,
              fill: "#525866",
            }}
          />
          <ZAxis dataKey="ticker" range={[80, 80]} />
          <ReferenceLine y={0} stroke="#0b1f3a" strokeDasharray="2 2" />
          <ReferenceLine x={0} stroke="#0b1f3a" strokeDasharray="2 2" />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const p = payload[0].payload as ScatterPoint;
              return (
                <div className="bg-page border border-line px-3 py-2 text-xs shadow-lg">
                  <p className="font-mono text-ink font-medium">{p.ticker}</p>
                  <p className="text-ink-mid">
                    CAR: <span className="text-ink">{FMT_PCT(p.car)}</span>
                  </p>
                  <p className="text-ink-mid">
                    Volume lift:{" "}
                    <span className="text-ink">{FMT_PCT(p.volumeLift)}</span>
                  </p>
                  <p className="eyebrow mt-1">{p.cohort}</p>
                </div>
              );
            }}
          />
          <Scatter
            name="Treatment"
            data={treatment}
            fill="#2251ff"
            opacity={0.85}
          >
            {treatment.map((p) => (
              <Cell key={p.ticker} fill="#2251ff" />
            ))}
          </Scatter>
          <Scatter
            name="Control"
            data={control}
            fill="#0e7a3e"
            opacity={0.7}
          >
            {control.map((p) => (
              <Cell key={p.ticker} fill="#0e7a3e" />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="mt-2 flex items-center gap-4 text-xs text-ink-mid">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-accent" />
          Treatment (T1/T2/T3)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-signal-gain" />
          Control (STI-30)
        </span>
      </div>
    </div>
  );
}
