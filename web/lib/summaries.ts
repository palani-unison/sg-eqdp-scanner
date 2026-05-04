import { createClient } from "@/lib/supabase/server";
import type { CohortRow } from "@/components/charts/CumulativeReturnsChart";
import type { ScatterPoint } from "@/components/charts/BeneficiaryScatter";

export async function loadCohortTimeseries(): Promise<CohortRow[]> {
  const supabase = await createClient();
  const PAGE = 1000;
  const rows: CohortRow[] = [];
  let offset = 0;
  while (true) {
    const { data } = await supabase
      .from("cohort_timeseries")
      .select("trade_date, treatment_cum, control_cum, sti_cum")
      .order("trade_date")
      .range(offset, offset + PAGE - 1);
    if (!data?.length) break;
    for (const r of data) {
      rows.push({
        date: r.trade_date as string,
        treatment: r.treatment_cum === null ? null : Number(r.treatment_cum),
        control: r.control_cum === null ? null : Number(r.control_cum),
        sti: r.sti_cum === null ? null : Number(r.sti_cum),
      });
    }
    if (data.length < PAGE) break;
    offset += PAGE;
  }
  return rows;
}

export async function loadBeneficiaryScatter(): Promise<ScatterPoint[]> {
  const supabase = await createClient();
  const { data: summaries } = await supabase
    .from("ticker_summaries")
    .select("ticker, car_total, volume_lift_pct")
    .limit(1000);
  const { data: tickers } = await supabase
    .from("tickers")
    .select("ticker, in_sti30, t1_flag, t2_flag, t3_flag")
    .limit(1000);

  const cohortOf = new Map<string, ScatterPoint["cohort"]>();
  for (const t of tickers ?? []) {
    if (t.in_sti30) cohortOf.set(t.ticker, "control");
    else if (t.t1_flag || t.t2_flag || t.t3_flag) cohortOf.set(t.ticker, "treatment");
    else cohortOf.set(t.ticker, "other");
  }

  return (summaries ?? [])
    .filter(
      (r) =>
        r.car_total !== null &&
        r.volume_lift_pct !== null &&
        Number.isFinite(Number(r.car_total)) &&
        Number.isFinite(Number(r.volume_lift_pct))
    )
    .map((r) => ({
      ticker: r.ticker as string,
      car: Number(r.car_total),
      volumeLift: Number(r.volume_lift_pct),
      cohort: cohortOf.get(r.ticker) ?? "other",
    }));
}
