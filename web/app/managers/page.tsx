import Link from "next/link";
import { EditorialHeader } from "@/components/EditorialHeader";

export const metadata = { title: "EQDP fund houses" };

type Manager = {
  name: string;
  tranche: 1 | 2;
  href: string;
  role: string;
  notes: string;
};

const MANAGERS: Manager[] = [
  {
    name: "Avanda Investment Management",
    tranche: 1,
    href: "https://www.avandaim.com",
    role: "Singapore-based active",
    notes:
      "Long-running Asia-ex-Japan focus with existing institutional infrastructure suitable for absorbing concentrated SGX positions.",
  },
  {
    name: "Fullerton Fund Management",
    tranche: 1,
    href: "https://www.fullertonfund.com",
    role: "Temasek-owned",
    notes:
      "Deep familiarity with the SGX-listed universe and Temasek-linked governance. Plausible bias toward larger, more institutionally-friendly mid-caps.",
  },
  {
    name: "JPMorgan Asset Management",
    tranche: 1,
    href: "https://am.jpmorgan.com",
    role: "Global (US)",
    notes:
      "Substantial Asian-equities desks. Files internationally under multiple legal entities — alias resolution required when cross-checking SGXNet.",
  },
  {
    name: "Amova Asset Management",
    tranche: 2,
    href: "https://www.amova.com",
    role: "Asia regional",
    notes:
      "Rebranded from Nikko Asset Management Asia in 2025. Substantial-shareholder filings before the rebrand may surface under the legacy Nikko AM name.",
  },
  {
    name: "AR Capital",
    tranche: 2,
    href: "",
    role: "Singapore boutique",
    notes:
      "Smallest of the appointed managers by AUM; expected to take more concentrated positions in fewer names.",
  },
  {
    name: "BlackRock",
    tranche: 2,
    href: "https://www.blackrock.com",
    role: "Global (US)",
    notes:
      "World's largest asset manager. Files under several legal entities — typically 'BlackRock Investment Management (Singapore) Pte. Ltd.' for active mandates.",
  },
  {
    name: "Eastspring Investments",
    tranche: 2,
    href: "https://www.eastspring.com",
    role: "Prudential-owned",
    notes:
      "Asian asset-management arm of Prudential plc. Long-tenured Singapore-equity team with quality / yield bias.",
  },
  {
    name: "Lion Global Investors",
    tranche: 2,
    href: "https://www.lionglobalinvestors.com",
    role: "OCBC / Great Eastern JV",
    notes:
      "Strong ETF presence on SGX; the EQDP mandate is meaningful incremental active capital.",
  },
  {
    name: "Manulife Investment Management",
    tranche: 2,
    href: "https://www.manulifeim.com",
    role: "Manulife-owned",
    notes:
      "Files variously as 'Manulife Investment Management' or 'Manulife Asset Management'. Active equity capability across Asia.",
  },
];

export default function ManagersPage() {
  const t1 = MANAGERS.filter((m) => m.tranche === 1);
  const t2 = MANAGERS.filter((m) => m.tranche === 2);
  return (
    <div className="px-6 sm:px-12 lg:px-20 py-16 max-w-article">
      <EditorialHeader
        eyebrow="Fund houses"
        title="The nine EQDP-appointed managers"
        dek="MAS does not disclose how the S$3.95 billion deployed so far is split between them. We treat each as an equally-likely buyer in the inferential model, then cross-check against SGXNet 5%-stake filings to identify confirmed buyers."
        meta="Reading time · 5 minutes"
        large
      />

      <Tranche
        label="Tranche 1"
        sub="Appointed 21 July 2025 · S$1.1 billion"
        managers={t1}
      />
      <Tranche
        label="Tranche 2"
        sub="Appointed 19 November 2025 · S$2.85 billion"
        managers={t2}
      />

      {/* Alias resolution note */}
      <section className="mt-16 border-t border-line pt-10">
        <div className="grid md:grid-cols-3 gap-8">
          <div>
            <p className="eyebrow">Method note</p>
            <div className="rule mt-2" />
            <h2 className="display text-2xl text-ink mt-4">
              How we map a filing back to a manager
            </h2>
          </div>
          <div className="md:col-span-2 text-ink-mid">
            <p>
              SGXNet 5%-stake filings carry the manager's <em>full legal entity
              name</em>, which is rarely the friendly name above.{" "}
              <strong>BlackRock</strong> can appear as <em>BlackRock Investment
              Management (Singapore) Pte. Ltd.</em>, <em>BlackRock Asset
              Management North Asia Limited</em>, or <em>BlackRock Fund
              Advisors</em>.
            </p>
            <p className="mt-4">
              Our scraper resolves these aliases to a single canonical{" "}
              <code className="text-xs bg-line/60 px-1.5 py-0.5 rounded">
                manager_id
              </code>{" "}
              using a per-manager pattern list maintained in{" "}
              <code className="text-xs bg-line/60 px-1.5 py-0.5 rounded">
                scrapers/sgxnet/manager_aliases.py
              </code>
              .
            </p>
          </div>
        </div>
      </section>

      <section className="mt-16 border-t border-line pt-8 text-sm text-ink-mid flex flex-wrap gap-x-6">
        <span className="eyebrow">Continue</span>
        <Link href="/methodology" className="hover:text-ink">
          Methodology →
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

function Tranche({
  label,
  sub,
  managers,
}: {
  label: string;
  sub: string;
  managers: Manager[];
}) {
  return (
    <section className="mt-16">
      <div className="flex flex-wrap items-baseline justify-between gap-4 border-b border-line pb-4">
        <div>
          <p className="eyebrow">{label}</p>
          <h2 className="display text-3xl text-ink mt-2">{sub.split(" · ")[0]}</h2>
        </div>
        <p className="stat-num text-2xl text-accent">{sub.split(" · ")[1]}</p>
      </div>
      <div className="grid sm:grid-cols-2 gap-px bg-line mt-6">
        {managers.map((m) => (
          <article key={m.name} className="bg-page p-6 group">
            <p className="eyebrow">{m.role}</p>
            <h3 className="display text-xl text-ink mt-3">
              {m.href ? (
                <a
                  href={m.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-accent transition-colors"
                >
                  {m.name} <span className="text-accent">↗</span>
                </a>
              ) : (
                m.name
              )}
            </h3>
            <p className="text-sm text-ink-mid mt-3 leading-relaxed">{m.notes}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
