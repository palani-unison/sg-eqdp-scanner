"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

function RegisterForm() {
  const params = useSearchParams();
  const next = params.get("next") || "/brief";
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [firm, setFirm] = useState("");
  const [country, setCountry] = useState("");
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!agree) {
      setStatus("Please accept the disclaimer.");
      return;
    }
    setBusy(true);
    setStatus(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        data: {
          name,
          firm: firm || null,
          country: country || null,
          disclaimer_accepted_at: new Date().toISOString(),
        },
      },
    });
    setBusy(false);
    if (error) setStatus(`Error: ${error.message}`);
    else setStatus("Check your email for the magic link.");
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-semibold text-ink">Read the Brief</h1>
      <p className="mt-2 text-sm text-ink-mid">
        Free. Email-gated so we know who's reading. One unsubscribe click ends emails forever.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-4">
        <Field label="Name" id="name" value={name} onChange={setName} required />
        <Field label="Email" id="email" type="email" value={email} onChange={setEmail} required />
        <Field label="Firm (optional)" id="firm" value={firm} onChange={setFirm} />
        <Field label="Country (optional)" id="country" value={country} onChange={setCountry} />

        <label className="flex items-start gap-2 text-sm text-ink-mid">
          <input
            type="checkbox"
            checked={agree}
            onChange={(e) => setAgree(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            I have read and accept the{" "}
            <Link href="/disclaimer" className="underline">
              Disclaimer
            </Link>
            . I understand this is the personal research of Palaniappan Chidambaram, that it is not investment advice, and that the analysis is inferential because MAS does not disclose specific EQDP holdings.
          </span>
        </label>

        <button
          type="submit"
          disabled={busy || !agree}
          className="w-full rounded-md bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-ink-soft disabled:opacity-50"
        >
          {busy ? "Sending..." : "Send magic link"}
        </button>

        {status && <p className="text-sm text-ink-mid">{status}</p>}
      </form>
    </div>
  );
}

function Field({
  label,
  id,
  type = "text",
  value,
  onChange,
  required,
}: {
  label: string;
  id: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block w-full rounded-md border border-ink/20 px-3 py-2 text-sm focus:border-accent focus:outline-none"
      />
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-md px-4 py-16">Loading...</div>}>
      <RegisterForm />
    </Suspense>
  );
}
