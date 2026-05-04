import { createClient } from "@/lib/supabase/server";
import type { EventStudyRow } from "@/components/charts/EventStudyChart";
import type { DiDPoint } from "@/components/charts/DiDForestChart";

const EVENT_LABELS: Record<string, string> = {
  announcement: "MAS announcement (2025-02-21, S$5B)",
  tranche_1: "Tranche 1 deployment (2025-07-21, S$1.1B → 3 managers)",
  tranche_2: "Tranche 2 deployment (2025-11-19, S$2.85B → 6 managers)",
  expansion: "Programme expansion (2026-02-12, S$6.5B)",
};

export const EVENT_ORDER = ["announcement", "tranche_1", "tranche_2", "expansion"] as const;
export type EventId = (typeof EVENT_ORDER)[number];

/**
 * For each event, fetch ar_capm rows and build the per-t cross-sectional
 * mean of treated vs control CAR up to that t.
 *
 * Done in JS (one query per event) since Supabase REST doesn't expose a
 * cross-tabulated aggregation. Each event is bounded (~25 days × ~50 tickers)
 * so the per-t aggregation is cheap.
 */
export async function loadEventStudies(): Promise<
  { eventId: EventId; label: string; data: EventStudyRow[] }[]
> {
  const supabase = await createClient();

  // Find each ticker's tier so we can split AR rows into treated vs control.
  const { data: tickers } = await supabase
    .from("tickers")
    .select("ticker, in_sti30, t1_flag, t2_flag, t3_flag")
    .limit(1000);

  const tierOf = new Map<string, "treated" | "control" | "other">();
  for (const t of tickers ?? []) {
    if (t.in_sti30) tierOf.set(t.ticker, "control");
    else if (t.t1_flag || t.t2_flag || t.t3_flag) tierOf.set(t.ticker, "treated");
    else tierOf.set(t.ticker, "other");
  }

  const out: { eventId: EventId; label: string; data: EventStudyRow[] }[] = [];

  for (const eventId of EVENT_ORDER) {
    // Page through abnormal_returns for this event (~1300 rows max)
    const all: { ticker: string; t: number; ar: number | null; car: number | null }[] = [];
    const PAGE = 1000;
    let offset = 0;
    while (true) {
      const { data: rows } = await supabase
        .from("abnormal_returns")
        .select("ticker, t, ar, car")
        .eq("event_id", eventId)
        .eq("benchmark", "capm")
        .order("t")
        .range(offset, offset + PAGE - 1);
      if (!rows?.length) break;
      all.push(...rows);
      if (rows.length < PAGE) break;
      offset += PAGE;
    }

    // Group by t and compute mean CAR for treated vs control
    const byT = new Map<number, { tSum: number; tCount: number; cSum: number; cCount: number }>();
    for (const r of all) {
      const tier = tierOf.get(r.ticker);
      if (tier !== "treated" && tier !== "control") continue;
      if (r.car === null || r.car === undefined) continue;
      const acc = byT.get(r.t) ?? { tSum: 0, tCount: 0, cSum: 0, cCount: 0 };
      if (tier === "treated") {
        acc.tSum += r.car;
        acc.tCount += 1;
      } else {
        acc.cSum += r.car;
        acc.cCount += 1;
      }
      byT.set(r.t, acc);
    }

    const data: EventStudyRow[] = [...byT.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([t, agg]) => ({
        t,
        treated: agg.tCount ? agg.tSum / agg.tCount : null,
        control: agg.cCount ? agg.cSum / agg.cCount : null,
      }));

    out.push({ eventId, label: EVENT_LABELS[eventId] ?? eventId, data });
  }

  return out;
}

/** Forest-plot data: per-event δ + 5/95 CI from bootstrap_cis. */
export async function loadDiDForest(): Promise<DiDPoint[]> {
  const supabase = await createClient();
  const { data: rows } = await supabase
    .from("bootstrap_cis")
    .select("metric, scope, point_estimate, lower_5, upper_95")
    .eq("metric", "did_delta");

  if (!rows?.length) return [];

  // Stable order matching EVENT_ORDER
  const order = new Map<string, number>(EVENT_ORDER.map((e, i) => [e, i]));
  return rows
    .filter((r) => order.has(r.scope as string))
    .sort(
      (a, b) =>
        (order.get(a.scope as string) ?? 99) -
        (order.get(b.scope as string) ?? 99)
    )
    .map((r) => {
      const point = Number(r.point_estimate);
      const lo = Number(r.lower_5);
      const hi = Number(r.upper_95);
      return {
        event: (r.scope as string) ?? "?",
        point,
        lower: lo,
        upper: hi,
        significant: lo > 0 || hi < 0,
      };
    });
}
