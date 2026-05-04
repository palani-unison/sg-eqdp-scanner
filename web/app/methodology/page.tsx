import Link from "next/link";
import { EditorialHeader } from "@/components/EditorialHeader";

export const metadata = { title: "Methodology" };

export default function MethodologyPage() {
  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-article">
      <EditorialHeader
        eyebrow="Method"
        title="How we reverse-engineer who got bought"
        dek="MAS does not say which stocks the appointed managers bought. We infer it by keeping three things strictly separate so the answer doesn't pre-suppose itself."
        meta="Reading time · 8 minutes"
        large
      />

      {/* Three concerns */}
      <section className="mt-12">
        <div className="grid sm:grid-cols-3 gap-px bg-line">
          {[
            {
              num: "01",
              title: "Candidate detection",
              body: "Who plausibly got bought, using only signals that are not the outcome we're trying to explain.",
            },
            {
              num: "02",
              title: "Impact estimation",
              body: "For those candidates, did they outperform after stripping market, size, and time effects?",
            },
            {
              num: "03",
              title: "Confidence layer",
              body: "Bootstrap intervals and placebo tests so we know how much to trust the impact estimate.",
            },
          ].map((p) => (
            <div key={p.num} className="bg-page p-6">
              <p className="stat-num text-3xl text-accent">{p.num}</p>
              <h3 className="display text-lg text-ink mt-3">{p.title}</h3>
              <p className="text-sm text-ink-mid mt-2">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Biggest mistake */}
      <section className="mt-16">
        <figure className="border-l-2 border-accent pl-8 max-w-prose">
          <p className="eyebrow">The single biggest mistake to avoid</p>
          <blockquote className="display text-2xl text-ink mt-3 leading-snug">
            Don't measure returns with returns. A naïve "EQDP score" built from
            <em> price gain × volume change × momentum </em>identifies stocks
            that went up — but that is the question, not the answer.
          </blockquote>
        </figure>
        <p className="mt-6 max-w-prose text-ink-mid">
          The candidate score uses only inputs that are not the outcome:
        </p>
      </section>

      {/* Five signals */}
      <section className="mt-8 max-w-prose">
        <Signal
          weight="0.30"
          name="Liquidity rise"
          body={
            <>
              Change in 60-day rolling <em>Amihud illiquidity</em> from before
              each tranche to after. Lower Amihud = the same daily return
              achieved on more volume = a deeper market.
            </>
          }
        />
        <Signal
          weight="0.20"
          name="Institutional flow proxy"
          body={
            <>
              Fraction of the last 30 trading days where the close exceeded the
              same-day rolling 30-day dollar-volume-weighted price. A
              "sustained accumulation" tell.
            </>
          }
        />
        <Signal
          weight="0.15"
          name="Index inclusion"
          body={
            <>
              Dummy for membership in the iEdge SG Next 50 / mid-cap basket.
              EQDP managers favour names with existing institutional plumbing.
            </>
          }
        />
        <Signal
          weight="0.15"
          name="Broker-list presence"
          body={
            <>
              Count of public sell-side beneficiary lists naming the stock
              (RHB-30, Maybank-18, Edge-69, others), normalised to [0, 1].
            </>
          }
        />
        <Signal
          weight="0.20"
          name="Filing presence"
          body={
            <>
              Dummy for any SGXNet substantial-shareholder filing by an
              EQDP-appointed manager in the last 12 months. The only signal
              that, when present, is direct evidence rather than inference.
            </>
          }
        />
      </section>

      <p className="mt-10 max-w-prose text-ink-mid">
        The unit test in{" "}
        <code className="text-xs bg-line/60 px-1.5 py-0.5 rounded">
          tests/test_score.py
        </code>{" "}
        enforces this guarantee: feed the same flow signals with arbitrarily
        different cumulative returns, and the score is unchanged.
      </p>

      {/* Three-tier universe */}
      <section className="mt-16">
        <p className="eyebrow">Universe</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          The three-tier taxonomy
        </h2>
        <p className="mt-4 max-w-prose text-ink-mid">
          A stock can sit in multiple tiers; the highest tier wins for
          headline classification, but the <em>overlap and disagreement</em>{" "}
          between tiers is itself the finding.
        </p>
        <div className="mt-8 grid sm:grid-cols-2 gap-px bg-line">
          <Tier
            label="T1"
            name="Confirmed"
            body="≥1 of the nine EQDP-appointed managers has filed a substantial-shareholder disclosure (≥ 5% stake) on or after 21 July 2025. Direct evidence."
          />
          <Tier
            label="T2"
            name="Eligible"
            body="Programmatic eligibility filter: small/mid-cap, SGX Mainboard or Catalist, daily-traded, not in STI-30, not in restricted sectors."
          />
          <Tier
            label="T3"
            name="Named"
            body="Stock named by RHB-30, Maybank-18, Edge-69, or other public broker beneficiary notes."
          />
          <Tier
            label="—"
            name="Control"
            body="STI-30 large caps. EQDP de-emphasises these — the natural counterfactual for the matched-pair difference-in-differences."
          />
        </div>
      </section>

      {/* Outperformance maths */}
      <section className="mt-16">
        <p className="eyebrow">Impact estimation</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          Measuring "outperformance" rigorously
        </h2>
        <div className="mt-6 max-w-prose space-y-4 text-ink-mid">
          <p>
            For each event date we estimate each stock's market beta on a
            252-trading-day window ending 30 days <em>before</em> the
            announcement (so the estimation window cannot leak event-window
            information). Then we compute the daily abnormal return:
          </p>
          <pre className="font-mono text-sm bg-ink text-page px-5 py-4 overflow-x-auto">
{`AR_{i,t} = R_{i,t} − ( α_i + β_i · R_{market,t} )`}
          </pre>
          <p>
            and sum it over the event window to get the cumulative abnormal
            return (CAR). For each treated stock we also find a matched STI-30
            control on sector, beta, and pre-event Amihud — and run a two-way
            fixed-effects difference-in-differences regression on the matched
            panel:
          </p>
          <pre className="font-mono text-sm bg-ink text-page px-5 py-4 overflow-x-auto">
{`R_{i,t} = α_i + γ_t + δ · (Treated_i × Post_t) + ε_{i,t}`}
          </pre>
          <p>
            δ is the average daily abnormal return attributable to EQDP after
            the matched control absorbs everything we can match on.
          </p>
        </div>
      </section>

      {/* Bootstrap CI */}
      <section className="mt-16">
        <p className="eyebrow">Confidence</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          Cluster bootstrap, 5,000 replications
        </h2>
        <p className="mt-4 max-w-prose text-ink-mid">
          For each replication we resample treated tickers and control tickers
          separately with replacement, refit the panel regression, and record
          δ. The 5–95 percentile band is the confidence interval reported on
          every chart in the brief.
        </p>
      </section>

      {/* Honest limits */}
      <section className="mt-16 border-t border-line pt-10">
        <p className="eyebrow text-signal-flag">Honest limits</p>
        <div className="rule mt-2" />
        <ul className="mt-6 space-y-4 max-w-prose text-ink-mid">
          <li>
            <strong className="text-ink">Sub-5% positions are invisible.</strong>{" "}
            If a manager bought a large but sub-threshold position, the SGXNet
            filing layer never sees it, and the stock can only land in T2/T3 —
            never T1.
          </li>
          <li>
            <strong className="text-ink">SGX live scrape is currently
            Akamai-blocked.</strong> The weekly filings ingestion runs in
            fixture mode (manually-saved filing HTML) until a residential-proxy
            bypass is in place.
          </li>
          <li>
            <strong className="text-ink">The "why" is unobservable.</strong> We
            can show that a stock got bought; we can't say what the manager's
            thesis was.
          </li>
          <li>
            <strong className="text-ink">Inference is not proof.</strong> The
            brief states which stocks plausibly benefited — and which broker-
            named stocks the data <em>fails</em> to support.
          </li>
        </ul>
      </section>

      <section className="mt-16 border-t border-line pt-8 text-sm text-ink-mid flex flex-wrap gap-x-6">
        <span className="eyebrow">Continue</span>
        <Link href="/managers" className="hover:text-ink">
          Fund houses →
        </Link>
        <Link href="/market" className="hover:text-ink">
          Market context →
        </Link>
        <Link href="/brief" className="hover:text-ink">
          Read the Brief →
        </Link>
      </section>
    </div>
  );
}

function Signal({
  weight,
  name,
  body,
}: {
  weight: string;
  name: string;
  body: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[80px_1fr] gap-6 py-5 border-b border-line last:border-b-0">
      <div className="stat-num text-2xl text-accent">{weight}</div>
      <div>
        <p className="display text-lg text-ink">{name}</p>
        <p className="text-sm text-ink-mid mt-1 leading-relaxed">{body}</p>
      </div>
    </div>
  );
}

function Tier({
  label,
  name,
  body,
}: {
  label: string;
  name: string;
  body: string;
}) {
  return (
    <div className="bg-page p-6">
      <div className="flex items-baseline gap-3">
        <span className="stat-num text-3xl text-accent">{label}</span>
        <h3 className="display text-lg text-ink">{name}</h3>
      </div>
      <p className="text-sm text-ink-mid mt-3 leading-relaxed">{body}</p>
    </div>
  );
}
