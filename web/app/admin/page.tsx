import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Admin" };
export const dynamic = "force-dynamic";

export default async function AdminHomePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login?next=/admin");

  const adminEmail = process.env.ADMIN_EMAIL?.toLowerCase();
  if (!adminEmail || user.email?.toLowerCase() !== adminEmail) {
    redirect("/?error=admin_only");
  }

  const [{ count: totalUsers }, { count: totalScores }, { count: totalFilings }, { data: latestRuns }] =
    await Promise.all([
      supabase.from("user_profiles").select("user_id", { count: "exact", head: true }),
      supabase.from("candidate_scores").select("ticker", { count: "exact", head: true }),
      supabase.from("filings_t1").select("filing_id", { count: "exact", head: true }),
      supabase
        .from("pipeline_runs")
        .select("run_id, job_name, status, started_at, completed_at")
        .order("started_at", { ascending: false })
        .limit(8),
    ]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-2xl font-semibold text-ink">Admin</h1>
      <p className="mt-2 text-sm text-ink-mid">
        Signed in as <code className="text-ink">{user.email}</code>.
      </p>

      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        <Stat label="Registered users" value={totalUsers ?? 0} />
        <Stat label="Candidate scores (latest)" value={totalScores ?? 0} />
        <Stat label="T1 filings" value={totalFilings ?? 0} />
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">Recent pipeline runs</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm border border-ink/10">
            <thead className="bg-ink/5 text-ink-mid">
              <tr>
                <th className="text-left px-3 py-2">Job</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2">Started</th>
                <th className="text-left px-3 py-2">Completed</th>
              </tr>
            </thead>
            <tbody>
              {(latestRuns ?? []).map((r) => (
                <tr key={r.run_id} className="border-t border-ink/10">
                  <td className="px-3 py-2 font-mono text-xs">{r.job_name}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={r.status as string} />
                  </td>
                  <td className="px-3 py-2 text-ink-mid">{r.started_at}</td>
                  <td className="px-3 py-2 text-ink-mid">{r.completed_at ?? "—"}</td>
                </tr>
              ))}
              {!latestRuns?.length && (
                <tr>
                  <td colSpan={4} className="px-3 py-4 text-ink-mid text-center">
                    No runs yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">Quick links</h2>
        <ul className="mt-3 list-disc list-inside text-ink-mid space-y-1">
          <li>
            <Link href="/admin/users" className="underline">
              Registered users (full list)
            </Link>
          </li>
          <li>
            <Link href="/brief" className="underline">
              View the Brief (gated)
            </Link>
          </li>
          <li>
            <Link href="/tracker" className="underline">
              Live tracker
            </Link>
          </li>
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-ink/10 p-4">
      <p className="text-xs uppercase tracking-widest text-ink-mid">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-ink">{value.toLocaleString()}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "succeeded"
      ? "bg-green-50 text-green-800 border-green-200"
      : status === "partial"
      ? "bg-warning-soft text-warning border-warning/30"
      : status === "failed"
      ? "bg-red-50 text-red-800 border-red-200"
      : "bg-ink/5 text-ink-mid border-ink/10";
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs ${color}`}>
      {status}
    </span>
  );
}
