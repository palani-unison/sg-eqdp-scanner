"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const next = params.get("next") || "/brief";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"magic" | "password">("magic");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleMagic(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setStatus(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    setBusy(false);
    if (error) setStatus(`Error: ${error.message}`);
    else setStatus("Magic link sent. Check your email.");
  }

  async function handlePassword(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setStatus(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) {
      setStatus(`Error: ${error.message}`);
      return;
    }
    router.push(next);
    router.refresh();
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-semibold text-ink">Sign in</h1>
      <p className="mt-2 text-sm text-ink-mid">
        Magic link by default. Admins may sign in with a password.
      </p>

      <div className="mt-6 inline-flex rounded-md border border-ink/15 p-0.5">
        <button
          type="button"
          onClick={() => setMode("magic")}
          className={`px-3 py-1.5 text-sm rounded ${mode === "magic" ? "bg-ink text-white" : "text-ink"}`}
        >
          Magic link
        </button>
        <button
          type="button"
          onClick={() => setMode("password")}
          className={`px-3 py-1.5 text-sm rounded ${mode === "password" ? "bg-ink text-white" : "text-ink"}`}
        >
          Password (admin)
        </button>
      </div>

      <form onSubmit={mode === "magic" ? handleMagic : handlePassword} className="mt-6 space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-ink">Email</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-ink/20 px-3 py-2 text-sm focus:border-accent focus:outline-none"
          />
        </div>

        {mode === "password" && (
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-ink">Password</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-ink/20 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-ink-soft disabled:opacity-50"
        >
          {busy ? "Working..." : mode === "magic" ? "Send magic link" : "Sign in"}
        </button>

        {status && <p className="text-sm text-ink-mid">{status}</p>}
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-md px-4 py-16">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
