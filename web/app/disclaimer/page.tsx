import { EditorialHeader } from "@/components/EditorialHeader";

export const metadata = { title: "Disclaimer" };

export default function DisclaimerPage() {
  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-article">
      <EditorialHeader
        eyebrow="Disclaimer"
        title="The fine print, plainly stated"
        dek="This site is the personal research of Palaniappan Chidambaram. It is not investment advice. Read this in full before relying on any number on this site."
      />

      <article className="prose mt-8 max-w-prose">
        <h2>About this work</h2>
        <p>
          This site presents the personal research of Palaniappan Chidambaram.
          It is not affiliated with, endorsed by, or representative of Unison
          Group, the Monetary Authority of Singapore, the Singapore Exchange,
          or any of the asset managers mentioned. Views expressed are the
          author's own.
        </p>

        <h2>Not investment advice</h2>
        <p>
          Nothing on this site constitutes investment advice, an offer to buy
          or sell securities, or a recommendation of any kind. The author is
          not a licensed financial adviser. Information is provided for
          research and educational purposes only. Readers must conduct their
          own due diligence and, where appropriate, consult a licensed adviser
          before making any investment decision.
        </p>

        <h2>Inferential nature of the analysis</h2>
        <p>
          The MAS Equity Market Development Programme does not publicly
          disclose which specific Singapore-listed companies its appointed
          managers have purchased. Beneficiary identification on this site is{" "}
          <em>inferential</em> — combining eligibility criteria, broker-
          research beneficiary lists, market-microstructure changes around
          event dates, and SGXNet substantial-shareholder filings (positions
          of 5% or more). Sub-5% positions are invisible to public filing;
          meaningful EQDP capital may be deployed in stocks that never appear
          in our T1 universe. Inference is not proof.
        </p>

        <h2>Data sources and accuracy</h2>
        <p>
          Price and volume data is sourced from Yahoo Finance via the{" "}
          <code className="text-xs">yfinance</code> library. Filing data is
          scraped from SGXNet. Programme-design and event-date information is
          drawn from public MAS press releases and accompanying media. While
          reasonable care is taken, no representation or warranty is made as
          to the accuracy, completeness, or timeliness of any information, and
          the author accepts no liability for any loss arising from reliance
          on it. Data may be delayed; cited timestamps reflect the most recent
          successful refresh.
        </p>

        <h2>Forward-looking statements</h2>
        <p>
          Any statement about future market behaviour or programme deployment
          is speculative and based on the author's interpretation of public
          information. Past performance does not indicate future results.
        </p>

        <h2>Conflicts of interest</h2>
        <p>
          The author may from time to time hold personal positions in
          securities discussed on this site. The author does not act on behalf
          of any client and receives no compensation from any party named in
          the analysis. Where a position is held, this will be disclosed in
          the relevant section.
        </p>

        <h2 id="privacy">Privacy and tracking</h2>
        <p>
          Registered users provide name and email to access full content. The
          site logs which sections each session views and when. Data is stored
          on Supabase infrastructure. The author will not share email
          addresses with third parties. One-click unsubscribe is available on
          every email and from the user profile page.
        </p>

        <h2>Contact</h2>
        <p>
          Questions, corrections, or take-down requests:{" "}
          <a href="mailto:palani@unisongroup.com" className="text-accent">
            palani@unisongroup.com
          </a>
          .
        </p>
      </article>
    </div>
  );
}
