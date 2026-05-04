import Link from "next/link";
import { MarketChart } from "@/components/charts/MarketChart";
import { EditorialHeader } from "@/components/EditorialHeader";
import {
  EQDP_EVENT_DATES,
  loadStiCumulative,
  summariseSti,
} from "@/lib/market";

export const metadata = { title: "Market context" };
export const revalidate = 21600;

export default async function MarketPage() {
  const rows = await loadStiCumulative("2024-01-02");
  const summary = summariseSti(rows);

  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-7xl">
      <EditorialHeader
        eyebrow="Market"
        title="STI through the EQDP period"
        dek="The Straits Times Index is the natural reference for the SGX large-cap baseline. Because EQDP de-emphasises STI-30 names, the index serves as our event-study counterfactual."
        meta="Updated daily · 6-hour ISR"
        large
      />

      <section className="mt-10">
        <MarketChart data={rows} events={EQDP_EVENT_DATES} />
        <p className="text-xs text-ink-faint mt-3 max-w-prose">
          Cumulative log-return on the STI from {summary?.start ?? "—"}, daily.
          Vertical markers: programme announcement (Feb 2025), Tranche 1 (Jul
          2025), Tranche 2 (Nov 2025), Expansion (Feb 2026). Source:{" "}
          <code className="text-xs">factor_returns</code> table populated by
          the daily pipeline.
        </p>
      </section>

      {summary && (
        <section className="mt-12 border-y border-line bg-line-soft/50">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-line">
            <Stat
              label="Total return (since baseline)"
              value={fmtPct(summary.totalReturn)}
              window={`${summary.start} → ${summary.end}`}
            />
            <Stat
              label="Since announcement"
              value={fmtPct(summary.fromAnnouncement)}
              window="2025-02-21 → today"
            />
            <Stat
              label="Since Tranche 1"
              value={fmtPct(summary.fromTranche1)}
              window="2025-07-21 → today"
            />
            <Stat
              label="Since Tranche 2"
              value={fmtPct(summary.fromTranche2)}
              window="2025-11-19 → today"
            />
          </div>
        </section>
      )}

      <section className="mt-16 grid lg:grid-cols-3 gap-12">
        <div>
          <p className="eyebrow">How to read this</p>
          <div className="rule mt-2" />
          <h2 className="display text-2xl text-ink mt-4">
            Why a "did STI go up?" comparison isn't enough
          </h2>
        </div>
        <div className="lg:col-span-2 text-ink-mid space-y-4 max-w-prose">
          <p>
            A simple "did the market go up since the EQDP announcement"
            comparison is suggestive but not informative — global macro, rate
            cycles, and a regional re-rating all move STI alongside whatever
            EQDP does. The purpose of the methodology elsewhere on this site
            is to <Link href="/methodology" className="text-accent">strip
            these confounders out</Link> using matched-pair difference-in-
            differences with entity + time fixed effects.
          </p>
          <p>
            The headline result of that decomposition: only{" "}
            <strong>tranche_2</strong> — the actual S$2.85bn deployment in Nov
            2025 — shows a statistically significant positive treatment effect
            on the matched cohort versus STI-30 controls. See the{" "}
            <Link href="/brief" className="text-accent">Brief</Link>{" "}
            (email-gated) for the per-event δ forest plot with bootstrap CIs.
          </p>
        </div>
      </section>

      <section className="mt-16 border-t border-line pt-8 text-sm text-ink-mid flex flex-wrap gap-x-6">
        <span className="eyebrow">Continue</span>
        <Link href="/programme" className="hover:text-ink">
          What is EQDP? →
        </Link>
        <Link href="/methodology" className="hover:text-ink">
          Methodology →
        </Link>
        <Link href="/brief" className="hover:text-ink">
          Read the Brief →
        </Link>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  window,
}: {
  label: string;
  value: string;
  window: string;
}) {
  const positive = value.startsWith("+");
  return (
    <div className="bg-page p-6">
      <p className="eyebrow">{label}</p>
      <p
        className={`stat-num text-3xl mt-2 ${
          positive
            ? "text-signal-gain"
            : value === "0.00%"
            ? "text-ink"
            : "text-signal-loss"
        }`}
      >
        {value}
      </p>
      <p className="text-xs text-ink-faint mt-1">{window}</p>
    </div>
  );
}

function fmtPct(x: number): string {
  const pct = x * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}
