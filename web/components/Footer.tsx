import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-line mt-24">
      <div className="mx-auto max-w-7xl px-6 sm:px-10 py-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="display text-2xl text-ink">
            EQDP <span className="text-accent italic">Brief</span>
          </p>
          <p className="text-sm text-ink-mid mt-2 max-w-md">
            Forensic public-data inference of MAS Equity Market Development
            Programme beneficiaries. Personal research, not investment advice.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-mid">
          <Link href="/programme" className="hover:text-ink">
            Programme
          </Link>
          <Link href="/managers" className="hover:text-ink">
            Fund houses
          </Link>
          <Link href="/methodology" className="hover:text-ink">
            Methodology
          </Link>
          <Link href="/market" className="hover:text-ink">
            Market
          </Link>
          <Link href="/disclaimer" className="hover:text-ink">
            Disclaimer
          </Link>
        </nav>
      </div>
      <div className="border-t border-line">
        <div className="mx-auto max-w-7xl px-6 sm:px-10 py-4 text-xs text-ink-faint flex flex-col sm:flex-row sm:justify-between gap-2">
          <span>
            © {new Date().getFullYear()} Palaniappan Chidambaram.
          </span>
          <span>
            Built with Next.js, Supabase, Vercel · Open-source · MIT licence
          </span>
        </div>
      </div>
    </footer>
  );
}
