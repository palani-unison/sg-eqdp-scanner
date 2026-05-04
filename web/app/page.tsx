import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="px-6 sm:px-12 lg:px-20 pt-20 sm:pt-28 pb-16 max-w-7xl">
        <p className="eyebrow">EQDP Brief · Issue 01 · 2026</p>
        <div className="rule mt-3" />
        <h1 className="display-large text-4xl sm:text-6xl lg:text-7xl text-ink mt-6 max-w-4xl">
          Which Singapore-listed companies actually benefited from
          the EQDP?
        </h1>
        <p className="dek mt-6 max-w-2xl">
          MAS deployed S$6.5 billion through nine appointed asset managers but
          does not disclose specific holdings. This brief reverse-engineers who
          got bought — using only public data, with explicit confidence
          intervals on every claim.
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            href="/register"
            className="inline-flex items-center bg-ink text-page px-6 py-3 text-sm font-medium tracking-wide hover:bg-accent-deep transition-colors"
          >
            Read the Brief — free, email gated →
          </Link>
          <Link
            href="/programme"
            className="inline-flex items-center border border-ink/20 px-6 py-3 text-sm font-medium tracking-wide text-ink hover:border-ink transition-colors"
          >
            Start with the programme
          </Link>
        </div>
      </section>

      {/* Number stats — KPMG-style */}
      <section className="border-y border-line bg-line-soft/40">
        <div className="mx-auto max-w-7xl px-6 sm:px-12 lg:px-20 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
          <Stat number="S$6.5B" label="EQDP capital deployed" />
          <Stat number="9" label="Appointed managers" />
          <Stat number="4" label="Programme events tracked" />
          <Stat number="69" label="SGX names in the universe" />
        </div>
      </section>

      {/* Three-pillar method block */}
      <section className="px-6 sm:px-12 lg:px-20 py-20 max-w-7xl">
        <div className="grid lg:grid-cols-3 gap-12">
          <div>
            <p className="eyebrow">Method</p>
            <div className="rule mt-2" />
            <h2 className="display text-3xl sm:text-4xl text-ink mt-5">
              Three concerns kept strictly separate
            </h2>
            <p className="text-ink-mid mt-4 max-w-md">
              The single biggest mistake in this kind of analysis is to measure
              returns with returns. Our framework ensures the answer doesn't
              pre-suppose itself.
            </p>
          </div>

          <div className="lg:col-span-2 grid sm:grid-cols-3 gap-px bg-line">
            <Pillar
              num="01"
              title="Candidate detection"
              body="Who plausibly got bought, using only signals that are not the outcome — liquidity rise, sustained institutional flow, broker-list presence, filing presence."
            />
            <Pillar
              num="02"
              title="Impact estimation"
              body="For those candidates, did they outperform after stripping out beta, size, and time effects? CAPM-adjusted abnormal returns plus matched-pair difference-in-differences."
            />
            <Pillar
              num="03"
              title="Confidence layer"
              body="Block-bootstrap intervals, placebo tests on non-event dates, and out-of-sample stress tests. Every headline number ships with a CI."
            />
          </div>
        </div>
      </section>

      {/* Featured links */}
      <section className="px-6 sm:px-12 lg:px-20 py-16 max-w-7xl">
        <p className="eyebrow">Continue reading</p>
        <div className="rule mt-2" />
        <h2 className="display text-3xl sm:text-4xl text-ink mt-5">
          Where to start
        </h2>
        <div className="mt-10 grid md:grid-cols-2 gap-px bg-line">
          <FeaturedCard
            href="/programme"
            kicker="01 · Programme"
            title="What is the EQDP?"
            body="Timeline, capital breakdown, what MAS does and doesn't disclose, and the official sources."
          />
          <FeaturedCard
            href="/managers"
            kicker="02 · Fund houses"
            title="The nine appointed managers"
            body="BlackRock, JPMorgan, Eastspring, Manulife, Lion Global, Fullerton, Avanda, AR Capital, Amova — by tranche."
          />
          <FeaturedCard
            href="/methodology"
            kicker="03 · Method"
            title="How we reverse-engineer it"
            body="Plain-language walkthrough — candidate detection, impact estimation, bootstrap CIs, honest limits."
          />
          <FeaturedCard
            href="/market"
            kicker="04 · Market"
            title="STI through the EQDP period"
            body="Live cumulative-return chart with each tranche date marked. Summary by event window."
          />
        </div>
      </section>

      {/* The big "do not measure returns with returns" callout */}
      <section className="px-6 sm:px-12 lg:px-20 py-20 max-w-7xl">
        <figure className="border-l-2 border-accent pl-8 max-w-3xl">
          <p className="eyebrow">Editorial note</p>
          <blockquote className="display text-2xl sm:text-3xl text-ink mt-4 leading-tight">
            <span className="text-accent">"</span>The candidate-detection score
            does <em>not</em> use returns as inputs. A stock that rallied 245%
            gets a high candidate score only if the underlying flow signals
            fired — never simply because the price moved.
            <span className="text-accent">"</span>
          </blockquote>
          <figcaption className="mt-4 text-sm text-ink-mid">
            From the methodology — read more at{" "}
            <Link href="/methodology" className="text-accent hover:underline">
              /methodology
            </Link>
          </figcaption>
        </figure>
      </section>
    </div>
  );
}

function Stat({ number, label }: { number: string; label: string }) {
  return (
    <div>
      <p className="stat-num text-4xl sm:text-5xl text-ink">{number}</p>
      <p className="text-xs text-ink-mid mt-2 uppercase tracking-widest">
        {label}
      </p>
    </div>
  );
}

function Pillar({
  num,
  title,
  body,
}: {
  num: string;
  title: string;
  body: string;
}) {
  return (
    <div className="bg-page p-6">
      <p className="stat-num text-accent text-3xl">{num}</p>
      <h3 className="display text-xl text-ink mt-4">{title}</h3>
      <p className="text-sm text-ink-mid mt-3">{body}</p>
    </div>
  );
}

function FeaturedCard({
  href,
  kicker,
  title,
  body,
}: {
  href: string;
  kicker: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="group block bg-page p-8 hover:bg-line-soft/60 transition-colors"
    >
      <p className="eyebrow">{kicker}</p>
      <h3 className="display text-2xl sm:text-3xl text-ink mt-3 group-hover:text-accent transition-colors">
        {title}
      </h3>
      <p className="text-ink-mid mt-3">{body}</p>
      <p className="mt-5 text-xs uppercase tracking-widest text-ink-mid group-hover:text-accent">
        Continue →
      </p>
    </Link>
  );
}
