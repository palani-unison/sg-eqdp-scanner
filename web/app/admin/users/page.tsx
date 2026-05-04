import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Users · Admin" };
export const dynamic = "force-dynamic";

export default async function AdminUsersPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login?next=/admin/users");

  const adminEmail = process.env.ADMIN_EMAIL?.toLowerCase();
  if (!adminEmail || user.email?.toLowerCase() !== adminEmail) {
    redirect("/?error=admin_only");
  }

  const { data: profiles } = await supabase
    .from("user_profiles")
    .select("user_id, name, firm, country, registered_at, email_optin, unsubscribed_at")
    .order("registered_at", { ascending: false })
    .limit(500);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-2xl font-semibold text-ink">Registered users</h1>
      <p className="mt-2 text-sm text-ink-mid">
        Total: {profiles?.length ?? 0}
      </p>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm border border-ink/10">
          <thead className="bg-ink/5 text-ink-mid">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Firm</th>
              <th className="text-left px-3 py-2">Country</th>
              <th className="text-left px-3 py-2">Registered</th>
              <th className="text-left px-3 py-2">Subscribed</th>
            </tr>
          </thead>
          <tbody>
            {(profiles ?? []).map((p) => (
              <tr key={p.user_id} className="border-t border-ink/10">
                <td className="px-3 py-2">{p.name ?? "—"}</td>
                <td className="px-3 py-2 text-ink-mid">{p.firm ?? "—"}</td>
                <td className="px-3 py-2 text-ink-mid">{p.country ?? "—"}</td>
                <td className="px-3 py-2 text-ink-mid">{p.registered_at}</td>
                <td className="px-3 py-2">
                  {p.unsubscribed_at ? (
                    <span className="text-red-700">unsub</span>
                  ) : p.email_optin ? (
                    <span className="text-green-700">opted in</span>
                  ) : (
                    <span className="text-ink-mid">—</span>
                  )}
                </td>
              </tr>
            ))}
            {!profiles?.length && (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-ink-mid text-center">
                  No users yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
