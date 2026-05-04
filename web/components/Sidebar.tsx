"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type Item = { href: string; label: string; group: string };

const ITEMS: Item[] = [
  { group: "Read", href: "/", label: "Home" },
  { group: "Read", href: "/programme", label: "What is EQDP?" },
  { group: "Read", href: "/managers", label: "Fund houses" },
  { group: "Read", href: "/methodology", label: "Methodology" },
  { group: "Read", href: "/market", label: "Market context" },
  { group: "Read", href: "/risks", label: "Risks & scenarios" },
  { group: "Brief", href: "/brief", label: "The Brief" },
  { group: "Brief", href: "/tracker", label: "Live tracker" },
  { group: "About", href: "/about", label: "About" },
  { group: "About", href: "/disclaimer", label: "Disclaimer" },
];

type Props = {
  userEmail: string | null;
  isAdmin: boolean;
};

export function Sidebar({ userEmail, isAdmin }: Props) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const groups = Array.from(new Set(ITEMS.map((i) => i.group)));

  const sidebar = (
    <nav className="flex flex-col h-full w-64 shrink-0 border-r border-line bg-page px-6 py-7 text-sm">
      <Link
        href="/"
        className="display text-2xl text-ink mb-8 leading-none"
        onClick={() => setOpen(false)}
      >
        EQDP <span className="text-accent italic">Brief</span>
      </Link>

      {groups.map((g) => (
        <div key={g} className="mb-7">
          <p className="eyebrow mb-3">{g}</p>
          <ul className="space-y-0.5">
            {ITEMS.filter((i) => i.group === g).map((it) => {
              const active =
                it.href === "/"
                  ? pathname === "/"
                  : pathname?.startsWith(it.href) ?? false;
              return (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    onClick={() => setOpen(false)}
                    className={`block px-3 py-1.5 -mx-3 transition-colors ${
                      active
                        ? "text-ink font-medium border-l-2 border-accent bg-line/40"
                        : "text-ink-mid hover:text-ink hover:bg-line/30"
                    }`}
                  >
                    {it.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      {isAdmin && (
        <div className="mb-7">
          <p className="eyebrow mb-3 text-signal-flag">Admin</p>
          <ul className="space-y-0.5">
            <li>
              <Link
                href="/admin"
                onClick={() => setOpen(false)}
                className={`block px-3 py-1.5 -mx-3 ${
                  pathname?.startsWith("/admin") && pathname !== "/admin/users"
                    ? "text-ink font-medium border-l-2 border-signal-flag bg-signal-flagSoft/50"
                    : "text-ink-mid hover:text-ink hover:bg-line/30"
                }`}
              >
                Dashboard
              </Link>
            </li>
            <li>
              <Link
                href="/admin/users"
                onClick={() => setOpen(false)}
                className={`block px-3 py-1.5 -mx-3 ${
                  pathname === "/admin/users"
                    ? "text-ink font-medium border-l-2 border-signal-flag bg-signal-flagSoft/50"
                    : "text-ink-mid hover:text-ink hover:bg-line/30"
                }`}
              >
                Users
              </Link>
            </li>
          </ul>
        </div>
      )}

      <div className="mt-auto pt-6 border-t border-line">
        {userEmail ? (
          <>
            <p className="eyebrow mb-1">Signed in</p>
            <p className="text-xs text-ink truncate" title={userEmail}>
              {userEmail}
            </p>
            <form action="/auth/sign-out" method="POST" className="mt-3">
              <button
                type="submit"
                className="text-xs text-ink-mid hover:text-ink"
              >
                Sign out →
              </button>
            </form>
          </>
        ) : (
          <Link
            href="/login"
            onClick={() => setOpen(false)}
            className="block text-center text-xs font-medium tracking-wider uppercase border border-ink text-ink hover:bg-ink hover:text-page transition-colors px-4 py-2.5"
          >
            Sign in
          </Link>
        )}
      </div>
    </nav>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="sm:hidden sticky top-0 z-30 bg-page border-b border-line px-4 h-12 flex items-center justify-between">
        <Link href="/" className="display text-lg text-ink">
          EQDP <span className="text-accent italic">Brief</span>
        </Link>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs uppercase tracking-widest text-ink-mid"
          aria-label="Toggle menu"
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>

      {/* Mobile drawer */}
      {open && (
        <>
          <div
            className="sm:hidden fixed inset-0 z-30 bg-ink/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <div className="sm:hidden fixed top-12 left-0 z-40 h-[calc(100vh-3rem)] shadow-2xl">
            {sidebar}
          </div>
        </>
      )}

      {/* Desktop sticky sidebar */}
      <aside className="hidden sm:flex sticky top-0 h-screen">{sidebar}</aside>
    </>
  );
}
