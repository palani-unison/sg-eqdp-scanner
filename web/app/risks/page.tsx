import Link from "next/link";
import { EditorialHeader } from "@/components/EditorialHeader";

export const metadata = { title: "Risks & scenarios" };

const SCENARIOS = [
  {
    label: "Bull case",
    title: "EQDP flywheel fully engages",
    color: "signal-gain",
    body:
      "EQDP-anchored capital catalyses durable third-party institutional inflows. Sell-side coverage expands, IPO pipeline rebuilds, and SMID-cap turnover stays elevated even after MAS's S$6.5 bn is fully deployed. Treatment-cohort outperformance compounds over a multi-year horizon.",
    indicators: [
      "Sustained net inflows beyond the deployed amount.",
      "Sell-side initiations on T2/T3 stocks rising QoQ.",
      "Mainboard SMID-cap dollar volume holding > 1.5× pre-programme levels.",
    ],
  },
  {
    label: "Base case",
    title: "Gradual, steady deployment",
    color: "ink",
    body:
      "The programme deploys roughly on schedule. Treatment-cohort returns are positive but uneven across events; only the deployment-event windows show statistically significant treatment effects. Liquidity gains persist while EQDP capital is being put to work but partially fade after full deployment.",
    indicators: [
      "Tranche events continue to show positive δ in matched-pair DiD.",
      "Liquidity rise (Amihud Δ) decays slowly post-deployment.",
      "T1 confirmed-buyer list grows on each filing cycle.",
    ],
  },
  {
    label: "Bear case",
    title: "Liquidity-trap risk materialises",
    color: "signal-loss",
    body:
      "After the S$6.5 bn is fully deployed, third-party flow does not crowd in. Treatment-cohort excess returns reverse in 2027 as managers face redemption pressure and unwind concentrated SMID-cap positions. Citi's published warning of an EQDP \"liquidity trap\" — flows propping up valuations only while capital is being added — turns out to be prescient.",
    indicators: [
      "Treatment cohort cumulative return rolls over within 6 months of full deployment.",
      "T1 filings flip from acquisitions to crossings-down (stake reductions).",
      "SMID-cap dollar volume reverts to pre-2025 baseline.",
    ],
  },
];

export default function RisksPage() {
  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-article">
      <EditorialHeader
        eyebrow="Risks"
        title="What could go wrong with the EQDP thesis"
        dek="A clean read of who got bought is necessary but not sufficient. Even if our beneficiary identification is correct, the programme's ultimate impact depends on whether third-party capital follows EQDP capital into the SMID-cap segment — or doesn't."
        meta="Reading time · 5 minutes"
        large
      />

      {/* The headline risk */}
      <section className="mt-12">
        <figure className="border-l-2 border-signal-flag pl-8 max-w-prose">
          <p className="eyebrow text-signal-flag">The headline risk</p>
          <blockquote className="display text-2xl text-ink mt-3 leading-snug">
            Citi's published research has called out an EQDP{" "}
            <em>"liquidity trap"</em> risk — that institutional flows propping
            up SMID-cap valuations only persist while EQDP capital is being
            added, and reverse once the programme is fully deployed.
          </blockquote>
          <figcaption className="mt-4 text-sm text-ink-mid">
            We don't endorse the call, but it's the right framing — the
            programme's success is measured at the post-deployment horizon, not
            during deployment.
          </figcaption>
        </figure>
      </section>

      {/* Scenarios */}
      <section className="mt-16">
        <p className="eyebrow">Scenario analysis</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          Three paths from here
        </h2>
        <p className="mt-3 text-ink-mid max-w-prose">
          Each scenario is defined by an observable, not by a conclusion. The
          purpose is to know — in advance — what we'd need to see in the data
          for each case to be true.
        </p>

        <div className="mt-10 space-y-8">
          {SCENARIOS.map((s, i) => (
            <article
              key={s.label}
              className="border-l-2 pl-8 max-w-prose"
              style={{
                borderColor:
                  s.color === "signal-gain"
                    ? "#0e7a3e"
                    : s.color === "signal-loss"
                    ? "#a6291f"
                    : "#0b1f3a",
              }}
            >
              <p className="eyebrow">
                {String(i + 1).padStart(2, "0")} · {s.label}
              </p>
              <h3 className="display text-2xl text-ink mt-2">{s.title}</h3>
              <p className="mt-3 text-ink-mid">{s.body}</p>
              <p className="eyebrow mt-5">Watch for</p>
              <ul className="mt-2 space-y-1.5 text-sm text-ink-mid">
                {s.indicators.map((ind) => (
                  <li key={ind}>— {ind}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      {/* Other risks */}
      <section className="mt-16">
        <p className="eyebrow">Programme-specific risks</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">Other risks worth naming</h2>

        <div className="mt-8 grid sm:grid-cols-2 gap-px bg-line">
          <Risk
            title="Valuation stretch"
            body="Some EQDP-named beneficiaries already trade at meaningfully expanded multiples versus their pre-programme baselines. Re-rating without underlying earnings improvement is fragile."
          />
          <Risk
            title="Concentration in fewer names"
            body="With nine managers chasing a SMID-cap universe of perhaps 150 names, position-size overlap is highly likely. A coordinated unwind in any subset would have outsized price impact."
          />
          <Risk
            title="Sub-5% blind spot"
            body="A manager can deploy material capital below the 5% disclosure threshold. Our T1 universe sees only above-threshold positions; large but legitimately invisible holdings exist."
          />
          <Risk
            title="Manager-level risk"
            body="The S$2.55 bn dry powder concentrates further selection risk on a third batch of managers. Selection-criteria interpretation drives material outcome divergence."
          />
          <Risk
            title="Programme termination"
            body="EQDP is policy capital, not perpetual. A change in MAS leadership or fiscal stance could materially alter the deployment cadence or the dry-powder commitment."
          />
          <Risk
            title="Methodological risk on this site"
            body="Our matched-pair DiD assumes the matched control absorbs all confounders the model can match on. If a confounder we don't observe (e.g., specific export-cycle exposure) is correlated with treatment status, our δ is biased."
          />
        </div>
      </section>

      {/* Global comparables */}
      <section className="mt-16">
        <p className="eyebrow">Global precedents</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          Multi-year, not multi-month
        </h2>
        <div className="mt-6 grid sm:grid-cols-2 gap-px bg-line">
          <article className="bg-page p-6">
            <p className="eyebrow">Japan · 2014</p>
            <h3 className="display text-lg text-ink mt-2">
              GPIF allocation shift
            </h3>
            <p className="text-sm text-ink-mid mt-3">
              Japan's Government Pension Investment Fund rebalanced toward
              domestic equities in 2014. The full impact on Japanese small/mid-
              caps took 10+ years to play out and was punctuated by both
              compounding inflows and partial reversals as managers rotated.
            </p>
          </article>
          <article className="bg-page p-6">
            <p className="eyebrow">Korea · 2024</p>
            <h3 className="display text-lg text-ink mt-2">
              Value-Up programme
            </h3>
            <p className="text-sm text-ink-mid mt-3">
              Korea's "Value-Up" initiative (2024) targeted the chronic
              valuation discount in KOSPI. As of late 2025 it's still in early
              innings — the comparable data window is too short to draw
              durable inference for EQDP. We watch the sector but don't
              extrapolate.
            </p>
          </article>
        </div>
        <p className="mt-6 text-sm text-ink-mid max-w-prose">
          The implication is straightforward:{" "}
          <strong>
            judgements about EQDP's success made within 12 months of full
            deployment are likely to be wrong in either direction.
          </strong>
        </p>
      </section>

      <section className="mt-16 border-t border-line pt-8 text-sm text-ink-mid flex flex-wrap gap-x-6">
        <span className="eyebrow">Continue</span>
        <Link href="/methodology" className="hover:text-ink">
          Methodology →
        </Link>
        <Link href="/programme" className="hover:text-ink">
          Programme →
        </Link>
        <Link href="/brief" className="hover:text-ink">
          Read the Brief →
        </Link>
      </section>
    </div>
  );
}

function Risk({ title, body }: { title: string; body: string }) {
  return (
    <div className="bg-page p-6">
      <h3 className="display text-lg text-ink">{title}</h3>
      <p className="text-sm text-ink-mid mt-2 leading-relaxed">{body}</p>
    </div>
  );
}
