import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/brief";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      // Persist user_profile if it doesn't exist yet (best-effort).
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const md = (user.user_metadata ?? {}) as Record<string, unknown>;
        await supabase
          .from("user_profiles")
          .upsert(
            {
              user_id: user.id,
              name: (md.name as string) ?? user.email,
              firm: (md.firm as string | null) ?? null,
              country: (md.country as string | null) ?? null,
              disclaimer_accepted_at:
                (md.disclaimer_accepted_at as string) ?? new Date().toISOString(),
              email_optin: true,
            },
            { onConflict: "user_id" }
          );
      }
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
