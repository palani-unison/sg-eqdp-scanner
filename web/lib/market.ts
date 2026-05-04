import { createClient } from "@/lib/supabase/server";
import type { MarketRow } from "@/components/charts/MarketChart";

/**
 * Pull factor_returns.market (daily simple return on STI), compute cumulative
 * returns from a chosen baseline date, and return the (date, cum) series the
 * MarketChart wants.
 */
export async function loadStiCumulative(
  baselineDate: string = "2024-01-02"
): Promise<MarketRow[]> {
  const supabase = await createClient();
  const PAGE = 1000;
  let offset = 0;
  const rows: { trade_date: string; market: number }[] = [];
  while (true) {
    const { data } = await supabase
      .from("factor_returns")
      .select("trade_date, market")
      .gte("trade_date", baselineDate)
      .order("trade_date")
      .range(offset, offset + PAGE - 1);
    if (!data?.length) break;
    rows.push(...data);
    if (data.length < PAGE) break;
    offset += PAGE;
  }
  if (!rows.length) return [];

  let cum = 0;
  const out: MarketRow[] = [];
  for (const r of rows) {
    const ret = Number(r.market);
    if (!Number.isFinite(ret)) continue;
    // Compound additively in log-space for nicer chart math
    cum += Math.log(1 + ret);
    out.push({ date: r.trade_date, cum: Math.exp(cum) - 1 });
  }
  return out;
}

export const EQDP_EVENT_DATES = [
  { date: "2025-02-21", label: "Announcement" },
  { date: "2025-07-21", label: "Tranche 1" },
  { date: "2025-11-19", label: "Tranche 2" },
  { date: "2026-02-12", label: "Expansion" },
];

export type StiSummary = {
  start: string;
  end: string;
  totalReturn: number;
  fromAnnouncement: number;
  fromTranche1: number;
  fromTranche2: number;
};

export function summariseSti(rows: MarketRow[]): StiSummary | null {
  if (!rows.length) return null;
  const start = rows[0];
  const end = rows[rows.length - 1];
  const fromDate = (date: string): number => {
    const r = rows.find((x) => x.date >= date);
    return r ? end.cum - r.cum : 0;
  };
  return {
    start: start.date,
    end: end.date,
    totalReturn: end.cum,
    fromAnnouncement: fromDate("2025-02-21"),
    fromTranche1: fromDate("2025-07-21"),
    fromTranche2: fromDate("2025-11-19"),
  };
}
