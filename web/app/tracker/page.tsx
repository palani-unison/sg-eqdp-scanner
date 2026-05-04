import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Tracker" };
export const revalidate = 21600; // 6h ISR

export default async function TrackerPage() {
  const supabase = await createClient();

  const [{ data: latestRun }, { data: snapshot }] = await Promise.all([
    supabase
      .from("pipeline_runs")
      .select("job_name, status, completed_at")
      .eq("status", "succeeded")
      .order("completed_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from("candidate_scores")
      .select("score_date")
      .order("score_date", { ascending: false })
      .limit(1)
      .maybeSingle(),
  ]);

  const lastSuccessAt = latestRun?.completed_at as string | undefined;
  const stale =
    lastSuccessAt && (Date.now() - new Date(lastSuccessAt).getTime()) / 36e5 > 36;

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-2xl font-semibold text-ink">Live tracker</h1>
      <p className="mt-2 text-sm text-ink-mid">
        Refreshed daily after the close (Singapore time). Snapshot as of{" "}
        <strong>{snapshot?.score_date ?? "—"}</strong>.
      </p>

      {stale && (
        <div className="mt-4 rounded-md border border-warning/30 bg-warning-soft p-3 text-sm">
          Data is stale — last successful pipeline run completed {lastSuccessAt}. The team has been notified.
        </div>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-ink">Status</h2>
        <p className="mt-2 text-sm text-ink-mid">
          Last successful pipeline run: <code>{latestRun?.job_name ?? "—"}</code> at{" "}
          <code>{lastSuccessAt ?? "—"}</code>.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-ink">Next on the roadmap</h2>
        <ul className="mt-2 list-disc list-inside text-sm text-ink-mid space-y-1">
          <li>Sortable T1 / T2 / T3 ranking tables</li>
          <li>Latest filings feed</li>
          <li>Per-event programme-level CAR charts (with bootstrap CIs)</li>
        </ul>
      </section>
    </div>
  );
}
