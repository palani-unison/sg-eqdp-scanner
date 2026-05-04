import Link from "next/link";
import { EditorialHeader } from "@/components/EditorialHeader";

export const metadata = { title: "About" };

export default function AboutPage() {
  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-article">
      <EditorialHeader
        eyebrow="About"
        title="Personal research, public benefit"
        dek="A forensic, public-data inference of which Singapore-listed companies the MAS EQDP appointed managers actually bought — with explicit statistical confidence intervals and a clear non-beneficiary list."
        meta="Reading time · 3 minutes"
        large
      />

      <section className="prose mt-8 max-w-prose">
        <p>
          This site presents the personal research of{" "}
          <strong>Palaniappan Chidambaram</strong>. It is not affiliated with,
          endorsed by, or representative of Unison Group, the Monetary
          Authority of Singapore, the Singapore Exchange, or any of the asset
          managers mentioned. Views expressed are the author's own.
        </p>

        <h2>What this is</h2>
        <p>
          A reverse-engineering of EQDP beneficiaries using only public data:
          SGXNet substantial-shareholder filings, market-microstructure
          changes, broker beneficiary notes, and programmatic eligibility
          filters. No private channels, no disclosed-but-confidential MAS
          information, no off-the-record manager meetings.
        </p>

        <h2>Why a separate site</h2>
        <p>
          MAS does not publicly disclose which specific Singapore-listed
          companies its appointed managers have purchased. Beneficiary
          identification is <em>inferential</em> — combining eligibility
          criteria, market-microstructure changes, broker beneficiary lists,
          and SGXNet substantial-shareholder filings. Sub-5% positions are
          invisible to public filing; meaningful EQDP capital may be deployed
          in stocks that never appear in our T1 universe.
        </p>

        <h2>Method, in one paragraph</h2>
        <p>
          We separate <strong>candidate detection</strong> (who plausibly got
          bought, no return inputs) from <strong>impact estimation</strong>{" "}
          (did those names actually outperform after stripping market β,
          size, and value) from <strong>confidence</strong> (bootstrap CIs and
          placebo tests on the impact estimate). All Python code is open-source
          under MIT licence; every chart on this site maps to a Postgres query,
          a Python function, and a unit test.
        </p>

        <h2>Reproducibility commitment</h2>
        <p>
          A reader who clones the repository, runs{" "}
          <code className="text-xs">pipelines/backfill.py</code> followed by{" "}
          <code className="text-xs">pipelines/compute_metrics.py</code>{" "}
          followed by <code className="text-xs">pipelines/compute_did.py</code>
          {" "}should produce identical numbers. That is the credibility floor.
        </p>

        <h2>Contact</h2>
        <p>
          Corrections, take-down requests, or methodological challenges:{" "}
          <a href="mailto:palani@unisongroup.com" className="text-accent">
            palani@unisongroup.com
          </a>
          .
        </p>
      </section>

      <section className="mt-16 border-t border-line pt-8 text-sm text-ink-mid flex flex-wrap gap-x-6">
        <span className="eyebrow">Continue</span>
        <Link href="/methodology" className="hover:text-ink">
          Methodology →
        </Link>
        <Link href="/disclaimer" className="hover:text-ink">
          Full disclaimer →
        </Link>
      </section>
    </div>
  );
}
