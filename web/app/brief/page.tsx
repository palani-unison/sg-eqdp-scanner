import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { DiDForestChart } from "@/components/charts/DiDForestChart";
import { EventStudyChart } from "@/components/charts/EventStudyChart";
import { CumulativeReturnsChart } from "@/components/charts/CumulativeReturnsChart";
import { BeneficiaryScatter } from "@/components/charts/BeneficiaryScatter";
import { CsvExportButton } from "@/components/CsvExportButton";
import { EditorialHeader } from "@/components/EditorialHeader";
import {
  EVENT_ORDER,
  loadDiDForest,
  loadEventStudies,
} from "@/lib/event-study";
import {
  loadBeneficiaryScatter,
  loadCohortTimeseries,
} from "@/lib/summaries";
import { EQDP_EVENT_DATES } from "@/lib/market";

export const metadata = { title: "The Brief" };
export const dynamic = "force-dynamic";

type ScoreRow = {
  ticker: string;
  total_score: number | null;
  liquidity_rise: number | null;
  institutional_proxy: number | null;
  index_inclusion: number | null;
  broker_named: number | null;
  filing_present: number | null;
  eqdp_tier: string | null;
  score_date?: string | null;
};

export default async function BriefPage() {
  const supabase = await createClient();
  const { data: latestSnapshot } = await supabase
    .from("candidate_scores")
    .select("score_date")
    .order("score_date", { ascending: false })
    .limit(1)
    .maybeSingle();

  const snapshotDate = latestSnapshot?.score_date ?? null;

  const [{ data: top }, { data: full }, didForest, eventStudies, cohort, scatter] =
    await Promise.all([
      snapshotDate
        ? supabase
            .from("candidate_scores")
            .select(
              "ticker, total_score, liquidity_rise, institutional_proxy, index_inclusion, broker_named, filing_present, eqdp_tier"
            )
            .eq("score_date", snapshotDate)
            .order("total_score", { ascending: false })
            .limit(15)
        : Promise.resolve({ data: [] as ScoreRow[] }),
      snapshotDate
        ? supabase
            .from("candidate_scores")
            .select(
              "ticker, total_score, liquidity_rise, institutional_proxy, index_inclusion, broker_named, filing_present, eqdp_tier, score_date"
            )
            .eq("score_date", snapshotDate)
            .order("total_score", { ascending: false })
            .limit(500)
        : Promise.resolve({ data: [] as ScoreRow[] }),
      loadDiDForest(),
      loadEventStudies(),
      loadCohortTimeseries(),
      loadBeneficiaryScatter(),
    ]);

  // Pre-compute the CSV row sets so we can render the export buttons
  const scoresCsv = (full ?? []).map((r) => ({
    score_date: r.score_date,
    ticker: r.ticker,
    eqdp_tier: r.eqdp_tier,
    total_score: r.total_score,
    liquidity_rise: r.liquidity_rise,
    institutional_proxy: r.institutional_proxy,
    index_inclusion: r.index_inclusion,
    broker_named: r.broker_named,
    filing_present: r.filing_present,
  }));
  const cohortCsv = cohort.map((r) => ({
    trade_date: r.date,
    treatment_cum_log_return: r.treatment,
    control_cum_log_return: r.control,
    sti_cum_log_return: r.sti,
  }));
  const scatterCsv = scatter.map((p) => ({
    ticker: p.ticker,
    cohort: p.cohort,
    car_total: p.car,
    volume_lift_pct: p.volumeLift,
  }));
  const didCsv = didForest.map((d) => ({
    event: d.event,
    point_estimate: d.point,
    ci_lower_5pct: d.lower,
    ci_upper_95pct: d.upper,
    significant_at_90pct: d.significant ? 1 : 0,
  }));

  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-7xl">
      <EditorialHeader
        eyebrow={`The Brief · Snapshot ${snapshotDate ?? ""}`}
        title="Reverse-engineering EQDP beneficiaries"
        dek="The full forensic readout: programme-level treatment effect with bootstrap CIs, per-event abnormal returns, treatment-vs-control cumulative returns, beneficiary mapping, and the top-15 candidate scores."
        meta="Charts and tables read live from Supabase. Every number is exportable to CSV."
        large
      />

      {/* Programme-level DiD forest */}
      <section id="findings-programme" className="mt-16">
        <SectionHeader
          eyebrow="Headline result"
          title="Programme-level treatment effect"
          subtitle="Matched-pair difference-in-differences (entity + time FE) with cluster bootstrap CIs (5,000 reps)."
          actions={
            <CsvExportButton
              filename={`eqdp-did-bootstrap-${snapshotDate ?? "latest"}.csv`}
              rows={didCsv}
              label="Export DiD CSV"
            />
          }
        />
        <div className="mt-6">
          <DiDForestChart data={didForest} />
        </div>
        <p className="mt-4 text-sm text-ink-mid max-w-prose">
          Only <strong>tranche_2</strong> (S$2.85 bn deployed Nov 2025) shows a
          statistically significant positive treatment effect on the matched
          cohort — the only event whose 90% CI sits entirely above 0. The{" "}
          <strong>announcement</strong> event has a CI entirely below 0;
          markets favoured large-caps when the programme was first signalled,
          before any capital was deployed.
        </p>
      </section>

      {/* Cumulative returns: treatment vs control vs STI */}
      <section id="cumulative-returns" className="mt-20">
        <SectionHeader
          eyebrow="Cohort comparison"
          title="Cumulative returns: treatment vs control vs STI"
          subtitle="Mean cumulative log-return across each cohort, indexed to 2024-01-02. Vertical markers = EQDP event dates."
          actions={
            <CsvExportButton
              filename="eqdp-cohort-cumulative-returns.csv"
              rows={cohortCsv}
              label="Export cohort CSV"
            />
          }
        />
        <div className="mt-6">
          <CumulativeReturnsChart data={cohort} events={EQDP_EVENT_DATES} />
        </div>
      </section>

      {/* Beneficiary scatter */}
      <section id="beneficiary-map" className="mt-20">
        <SectionHeader
          eyebrow="Beneficiary map"
          title="Cumulative AR vs volume lift, per ticker"
          subtitle="Each dot is one ticker. CAR summed across the four EQDP events; volume lift = mean (post60d / pre60d − 1) across events."
          actions={
            <CsvExportButton
              filename="eqdp-beneficiary-scatter.csv"
              rows={scatterCsv}
              label="Export scatter CSV"
            />
          }
        />
        <div className="mt-6">
          <BeneficiaryScatter data={scatter} />
        </div>
      </section>

      {/* Per-event CAR paths */}
      <section id="event-studies" className="mt-20">
        <SectionHeader
          eyebrow="Event studies"
          title="Per-event CAR paths"
          subtitle="Treated mean cumulative abnormal return vs control mean by trading-day offset. CAPM-adjusted on a 252-day pre-event β window ending 30 days before the announcement."
        />
        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          {eventStudies.map((es) => (
            <EventStudyChart
              key={es.eventId}
              eventLabel={es.label}
              data={es.data}
            />
          ))}
        </div>
      </section>

      {/* Top candidate scores table */}
      <section id="findings-stock" className="mt-20">
        <SectionHeader
          eyebrow="Top candidate scores"
          title="Highest-plausibility EQDP beneficiaries (top 15)"
          subtitle="Returns are NOT an input. The score uses only liquidity rise, sustained institutional flow, index inclusion, broker-list presence, and filing presence."
          actions={
            <CsvExportButton
              filename={`eqdp-candidate-scores-${snapshotDate ?? "latest"}.csv`}
              rows={scoresCsv}
              label="Export full scores CSV"
            />
          }
        />
        <div className="mt-6 overflow-x-auto border border-line">
          <table className="w-full text-sm">
            <thead className="bg-line-soft text-ink-mid border-b border-line">
              <tr>
                <th className="text-left px-3 py-2.5 eyebrow !text-[10px]">#</th>
                <th className="text-left px-3 py-2.5 eyebrow !text-[10px]">Ticker</th>
                <th className="text-left px-3 py-2.5 eyebrow !text-[10px]">Tier</th>
                <th className="text-right px-3 py-2.5 eyebrow !text-[10px]">Liq Δ</th>
                <th className="text-right px-3 py-2.5 eyebrow !text-[10px]">Inst flow</th>
                <th className="text-right px-3 py-2.5 eyebrow !text-[10px]">Broker</th>
                <th className="text-right px-3 py-2.5 eyebrow !text-[10px]">Idx</th>
                <th className="text-right px-3 py-2.5 eyebrow !text-[10px]">Filing</th>
                <th className="text-right px-3 py-2.5 eyebrow !text-[10px]">Score</th>
              </tr>
            </thead>
            <tbody>
              {(top ?? []).map((r, i) => (
                <tr key={r.ticker} className="border-b border-line last:border-b-0 hover:bg-line-soft/50">
                  <td className="px-3 py-2.5 text-ink-faint stat-num">{i + 1}</td>
                  <td className="px-3 py-2.5 font-mono text-ink">{r.ticker}</td>
                  <td className="px-3 py-2.5">
                    <TierBadge tier={r.eqdp_tier} />
                  </td>
                  <td className="px-3 py-2.5 text-right stat-num">{fmt(r.liquidity_rise)}</td>
                  <td className="px-3 py-2.5 text-right stat-num">{fmt(r.institutional_proxy)}</td>
                  <td className="px-3 py-2.5 text-right stat-num">{fmt(r.broker_named)}</td>
                  <td className="px-3 py-2.5 text-right stat-num">{r.index_inclusion ?? 0}</td>
                  <td className="px-3 py-2.5 text-right stat-num">{r.filing_present ?? 0}</td>
                  <td className="px-3 py-2.5 text-right stat-num font-medium text-ink">
                    {fmt(r.total_score)}
                  </td>
                </tr>
              ))}
              {!top?.length && (
                <tr>
                  <td colSpan={9} className="px-3 py-6 text-ink-mid text-center">
                    No scores yet — pipeline has not produced a snapshot.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Limitations */}
      <section id="limitations" className="mt-20 border-t border-line pt-10">
        <SectionHeader
          eyebrow="Honest limits"
          title="What this analysis cannot answer"
        />
        <ul className="mt-6 space-y-3 max-w-prose text-ink-mid">
          <li>Sub-5% positions are invisible to public filings, undetectable from daily data alone.</li>
          <li>Intraday microstructure (bid-ask spreads, order-book depth) is out of scope until tick data is ingested.</li>
          <li><em>Why</em> a manager bought any specific stock is unobservable — we see the buy, not the thesis.</li>
          <li>Whether T3-named stocks that don't appear in T1 filings were considered and rejected, vs simply held below 5%.</li>
        </ul>
        <p className="mt-6 text-sm text-ink-mid">
          See <Link href="/methodology" className="text-accent">/methodology</Link> for
          the full analytical stack and{" "}
          <Link href="/programme" className="text-accent">/programme</Link> for
          MAS source documents.
        </p>
      </section>

      <span className="hidden">{EVENT_ORDER.join(",")}</span>
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-3">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <div className="rule mt-2" />
        <h2 className="display text-2xl sm:text-3xl text-ink mt-3">{title}</h2>
        {subtitle && (
          <p className="text-sm text-ink-mid mt-2 max-w-2xl">{subtitle}</p>
        )}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
}

function TierBadge({ tier }: { tier: string | null }) {
  const map: Record<string, string> = {
    T1: "bg-accent text-white",
    T2: "bg-accent-soft text-accent",
    T3: "bg-ink/10 text-ink",
    control: "bg-ink/5 text-ink-mid",
    none: "bg-ink/5 text-ink-mid",
  };
  const label = tier ?? "none";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs ${map[label] ?? map.none}`}>
      {label}
    </span>
  );
}

function fmt(x: number | null): string {
  if (x === null || x === undefined) return "—";
  return x.toFixed(3);
}
