import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export async function Nav() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const adminEmail = process.env.ADMIN_EMAIL?.toLowerCase();
  const isAdmin =
    !!user && !!adminEmail && user.email?.toLowerCase() === adminEmail;

  return (
    <header className="border-b border-ink/10 bg-white/70 backdrop-blur sticky top-0 z-30">
      <div className="mx-auto max-w-5xl px-4 h-14 flex items-center justify-between gap-4">
        <Link href="/" className="font-semibold text-ink tracking-tight">
          EQDP <span className="text-accent">Brief</span>
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/programme" className="text-ink-mid hover:text-ink">
            Programme
          </Link>
          <Link href="/managers" className="text-ink-mid hover:text-ink">
            Fund houses
          </Link>
          <Link href="/methodology" className="text-ink-mid hover:text-ink">
            Methodology
          </Link>
          <Link href="/market" className="text-ink-mid hover:text-ink">
            Market
          </Link>
          <Link
            href="/brief"
            className="text-ink hover:text-accent font-medium"
          >
            Brief
          </Link>
          {user ? (
            <>
              {isAdmin && (
                <Link
                  href="/admin"
                  className="text-ink-mid hover:text-ink hidden sm:inline"
                >
                  Admin
                </Link>
              )}
              <form action="/auth/sign-out" method="POST">
                <button
                  type="submit"
                  className="text-ink-mid hover:text-ink"
                >
                  Sign out
                </button>
              </form>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-md bg-ink px-3 py-1.5 text-white hover:bg-ink-soft text-xs"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
