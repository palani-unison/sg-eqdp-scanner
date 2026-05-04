import Link from "next/link";
import { EditorialHeader } from "@/components/EditorialHeader";

export const metadata = { title: "What is EQDP?" };

const TIMELINE = [
  {
    date: "2024-08-02",
    title: "Equities Market Review Group convened",
    capital: "—",
    note: "MAS sets up the working group, chaired by Minister Chee Hong Tat, to study how to revive Singapore's equity market.",
  },
  {
    date: "2025-02-21",
    title: "Programme announcement",
    capital: "S$5.0 bn",
    note: "Review Group's first set of measures lands. EQDP is born — explicit preference for SMID-cap allocations.",
  },
  {
    date: "2025-07-21",
    title: "Tranche 1 deployed",
    capital: "S$1.1 bn",
    note: "MAS appoints Avanda, Fullerton, JPMorgan Asset Management. First capital actually starts moving.",
  },
  {
    date: "2025-09",
    title: "iEdge Singapore Next 50 launched",
    capital: "—",
    note: "SGX rolls out a dedicated SMID-cap visibility index covering names ranked 31–80 by float-adjusted market cap.",
  },
  {
    date: "2025-10",
    title: "Avanda Singapore Discovery Fund goes live",
    capital: "—",
    note: "First EQDP-backed fund opens to accredited and institutional investors.",
  },
  {
    date: "2025-11-19",
    title: "Tranche 2 deployed",
    capital: "S$2.85 bn",
    note: "Six more managers appointed — Amova, AR Capital, BlackRock, Eastspring, Lion Global, Manulife. Companion measures: Nasdaq Dual-Listing Bridge and a S$30M Value Unlock Programme.",
  },
  {
    date: "2026-01-09",
    title: "Singapore Equities Forum 2026",
    capital: "—",
    note: "MAS Board Member Alvin Tan delivers the \"EQDP Reawakening\" keynote — programme ecosystem framing.",
  },
  {
    date: "2026-02-12",
    title: "Programme expansion",
    capital: "→ S$6.5 bn total",
    note: "Budget 2026 announces +S$1.5 bn top-up, taking the total programme size to S$6.5 billion.",
  },
];

const ELIGIBILITY = [
  {
    title: "Singapore-based",
    body: "The manager must be located in Singapore or have substantive Singapore operations. No box-ticking presence allowed.",
  },
  {
    title: "Track record in SGX names",
    body: "Demonstrated investment capability in Singapore-listed equities — not a generic Asian-equities pitch.",
  },
  {
    title: "Strategy alignment",
    body: "Proposed strategy must explicitly target liquidity improvement and broaden investor participation, with meaningful SMID-cap weighting.",
  },
  {
    title: "Third-party capital catalysis",
    body: "The manager must show plausible ability to crowd in commercial investor capital alongside the EQDP seed allocation.",
  },
  {
    title: "Developmental commitment",
    body: "Commitment to grow Singapore-based asset-management and research capabilities — staffing, presence, ecosystem investment.",
  },
  {
    title: "Active management only",
    body: "Passive and index-tracking strategies are explicitly ineligible. The mandate is to act, not to hug a benchmark.",
  },
];

const ECOSYSTEM = [
  {
    title: "iEdge Singapore Next 50 Index",
    body: "SGX's index of names ranked 31–80 by float-adjusted market cap — explicit visibility lever for the SMID-cap segment EQDP targets. Launched September 2025.",
  },
  {
    title: "Board lot size reduction",
    body: "SGX reduced standard board-lot sizes to lower the absolute capital threshold for retail participation in higher-priced SGX names.",
  },
  {
    title: "Nasdaq Dual-Listing Bridge",
    body: "A November-2025 SGX–Nasdaq pathway for cross-listing, designed to draw international flow into SGX-domiciled SMID-caps.",
  },
  {
    title: "Value Unlock Programme",
    body: "A S$30 million companion fund focused on catalysing strategic value-realisation moves at SGX-listed companies — buybacks, divestments, board engagement.",
  },
  {
    title: "IPO pipeline initiatives",
    body: "Coordinated effort to bring more Asian growth-stage listings onto the SGX Mainboard, broadening the universe of names EQDP can deploy into.",
  },
];

export default function ProgrammePage() {
  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-article">
      <EditorialHeader
        eyebrow="Programme"
        title={
          <>
            What is the <span className="text-accent italic">EQDP</span>?
          </>
        }
        dek="A S$6.5 billion bet that anchoring institutional active capital outside the STI-30 can deepen the long tail of SGX-listed equities. The programme has expanded twice and has S$2.55 billion still to deploy."
        meta="Reading time · 7 minutes"
        large
      />

      {/* Quick-fact stat strip */}
      <section className="mt-10 border-y border-line bg-line-soft/40">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-line">
          <Stat label="Total programme size" value="S$6.5B" sub="after Feb-2026 expansion" />
          <Stat label="Allocated to date" value="S$3.95B" sub="9 managers, 2 batches" />
          <Stat label="Remaining" value="S$2.55B" sub="dry powder" />
          <Stat label="Third batch expected" value="Mid-2026" sub="not yet announced" />
        </div>
      </section>

      <section className="prose mt-12 max-w-prose">
        <p>
          On <strong>21 February 2025</strong> the{" "}
          <a
            href="https://www.mas.gov.sg/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent"
          >
            Monetary Authority of Singapore (MAS)
          </a>{" "}
          launched the Equity Market Development Programme — capital allocated
          to a small set of fund managers with a mandate to invest in
          Singapore-listed equities, with explicit preference for{" "}
          <em>small- and mid-cap (SMID)</em> names. The policy aim: deepen
          liquidity and broaden institutional ownership of SGX-listed mid- and
          small-caps, the part of the market that has chronically suffered
          narrow trading and patchy research coverage.
        </p>

        <h2>Who funds it</h2>
        <p>
          EQDP is funded by MAS together with the Financial Sector Development
          Fund (FSDF). To rule out a common misconception:{" "}
          <strong>GIC and Temasek are not involved</strong> in administering
          the programme — this is regulator-led capital, not sovereign-wealth
          capital, and the distinction matters when reasoning about mandate
          flexibility.
        </p>

        <h2>What MAS does — and does not — disclose</h2>
        <p>
          MAS publicly discloses (a) the total size, (b) the dates of each
          tranche, and (c) the <strong>names</strong> of the appointed
          managers. It does <strong>not</strong> disclose: which specific
          stocks were bought, in what size, or how the capital is split between
          managers. That gap is the entire reason this brief exists. See{" "}
          <Link href="/methodology" className="text-accent">
            Methodology
          </Link>{" "}
          for how we close it inferentially using only public data.
        </p>
      </section>

      {/* Timeline */}
      <section className="mt-16">
        <p className="eyebrow">Timeline</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          Eighteen months of programme deployment
        </h2>
        <p className="mt-3 text-ink-mid max-w-prose">
          From the Equities Market Review Group's first meeting in August 2024
          to the Budget-2026 expansion announcement.
        </p>

        <ol className="mt-10 relative border-l border-line ml-3">
          {TIMELINE.map((e, i) => (
            <li key={e.date + e.title} className="ml-8 pb-10 last:pb-0">
              <span className="absolute -left-[7px] mt-2 w-3 h-3 rounded-full bg-accent border-2 border-page" />
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <p className="stat-num text-xs text-ink-faint tracking-widest uppercase">
                  {e.date}
                </p>
                <p className="text-xs text-ink-mid">
                  Event {String(i + 1).padStart(2, "0")} of {TIMELINE.length}
                </p>
              </div>
              <h3 className="display text-xl text-ink mt-2">{e.title}</h3>
              {e.capital !== "—" && (
                <p className="stat-num mt-1 text-accent text-sm">
                  {e.capital}
                </p>
              )}
              <p className="mt-2 text-ink-mid max-w-prose">{e.note}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Eligibility */}
      <section className="mt-16">
        <p className="eyebrow">Manager eligibility</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          The bar to be appointed
        </h2>
        <p className="mt-3 text-ink-mid max-w-prose">
          Six criteria gate which fund managers can be appointed. Read together
          they tell you what the programme is — and isn't — willing to allocate
          to.
        </p>
        <div className="mt-8 grid sm:grid-cols-2 gap-px bg-line">
          {ELIGIBILITY.map((c, i) => (
            <div key={c.title} className="bg-page p-6">
              <p className="stat-num text-accent text-2xl">
                {String(i + 1).padStart(2, "0")}
              </p>
              <h3 className="display text-lg text-ink mt-2">{c.title}</h3>
              <p className="text-sm text-ink-mid mt-2">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Investment guidelines */}
      <section className="mt-16">
        <p className="eyebrow">Investment guidelines</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">How managers must invest</h2>
        <div className="mt-6 grid lg:grid-cols-3 gap-12 max-w-prose">
          <div className="lg:col-span-2 text-ink-mid space-y-4">
            <p>
              MAS does not make day-to-day stock-selection decisions; managers
              have full discretion within the mandate. The constraints are
              minimal but defining:
            </p>
            <ul className="list-disc list-inside space-y-2">
              <li>
                Strategies must invest <em>fully or substantially</em> in
                Singapore public equities.
              </li>
              <li>
                Strategies with a higher allocation or tilt towards SMID-caps
                are preferred. No minimum SMID-cap percentage is mandated.
              </li>
              <li>Must be actively managed — passive products are ineligible.</li>
              <li>
                ASEAN ex-Singapore allocation up to roughly 40% has been{" "}
                <em>reported</em> by Macquarie Equity Research (citing
                industry contacts). This is <em>not</em> confirmed in MAS
                official documents and should be treated as soft information.
              </li>
            </ul>
          </div>
          <div>
            <p className="eyebrow">SGX market-cap convention</p>
            <div className="mt-3 border border-line p-4">
              <p className="text-sm">
                <strong className="text-ink">Small-cap:</strong>{" "}
                S$100 million — S$1 billion
              </p>
              <p className="text-sm mt-2">
                <strong className="text-ink">Mid-cap:</strong>{" "}
                S$1 billion — S$3 billion
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Programme ecosystem */}
      <section className="mt-16">
        <p className="eyebrow">Programme ecosystem</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl text-ink mt-5">
          The companion measures around EQDP
        </h2>
        <p className="mt-3 text-ink-mid max-w-prose">
          EQDP doesn't operate alone. MAS and SGX have rolled out a coordinated
          set of measures designed to compound the programme's effect on
          SGX-listed SMID-caps.
        </p>
        <div className="mt-8 grid sm:grid-cols-2 gap-px bg-line">
          {ECOSYSTEM.map((e) => (
            <div key={e.title} className="bg-page p-6">
              <h3 className="display text-lg text-ink">{e.title}</h3>
              <p className="text-sm text-ink-mid mt-2">{e.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="prose mt-16 max-w-prose">
        <p className="dek">
          Eighteen months in, the programme has deployed S$3.95 billion through
          nine managers, with S$2.55 billion still to allocate. Whether it is
          working — and for which stocks — is what this site investigates.
        </p>
      </section>

      {/* Sources */}
      <section className="mt-16 border-t border-line pt-10">
        <p className="eyebrow">Primary sources</p>
        <ul className="mt-5 space-y-3 text-sm text-ink-mid">
          <li>
            <a
              className="text-accent"
              href="https://www.mas.gov.sg/news/media-releases/2025"
              target="_blank"
              rel="noopener noreferrer"
            >
              MAS media releases (2025)
            </a>{" "}
            — programme announcement and tranche disclosures.
          </li>
          <li>
            <a
              className="text-accent"
              href="https://www.sgx.com/securities/company-announcements"
              target="_blank"
              rel="noopener noreferrer"
            >
              SGXNet company announcements
            </a>{" "}
            — substantial-shareholder filings (≥ 5%), the only public proof of
            who got bought.
          </li>
          <li>
            Major sell-side beneficiary lists referenced in this study: RHB-30,
            Maybank-18, Edge-69 (used as <em>candidates</em>, not as ground
            truth).
          </li>
        </ul>
      </section>

      <section className="mt-16 border-t border-line pt-8 text-sm text-ink-mid flex flex-wrap gap-x-6">
        <span className="eyebrow">Continue</span>
        <Link href="/managers" className="hover:text-ink">
          Fund houses →
        </Link>
        <Link href="/methodology" className="hover:text-ink">
          Methodology →
        </Link>
        <Link href="/risks" className="hover:text-ink">
          Risks →
        </Link>
        <Link href="/market" className="hover:text-ink">
          Market →
        </Link>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="bg-page p-6">
      <p className="eyebrow">{label}</p>
      <p className="stat-num text-2xl sm:text-3xl text-ink mt-1">{value}</p>
      <p className="text-xs text-ink-faint mt-1">{sub}</p>
    </div>
  );
}
