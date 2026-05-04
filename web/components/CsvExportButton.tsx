"use client";

import { useState } from "react";

type Props = {
  filename: string;
  rows: Record<string, unknown>[];
  label?: string;
};

/**
 * Small button that turns ``rows`` into a CSV file the browser downloads.
 * No server roundtrip; serialisation happens in-place.
 */
export function CsvExportButton({ filename, rows, label = "Download CSV" }: Props) {
  const [busy, setBusy] = useState(false);

  function handleClick() {
    if (!rows?.length) return;
    setBusy(true);
    try {
      const headers = Object.keys(rows[0]);
      const escape = (v: unknown): string => {
        if (v === null || v === undefined) return "";
        const s = typeof v === "string" ? v : String(v);
        // Quote if contains comma, quote, or newline
        if (/[",\n]/.test(s)) {
          return `"${s.replace(/"/g, '""')}"`;
        }
        return s;
      };
      const csv = [
        headers.join(","),
        ...rows.map((r) => headers.map((h) => escape(r[h])).join(",")),
      ].join("\n");

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={busy || !rows?.length}
      className="inline-flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase border border-ink/20 px-3 py-2 text-ink hover:border-ink hover:bg-ink hover:text-page transition-colors disabled:opacity-40"
    >
      <svg
        viewBox="0 0 16 16"
        width={12}
        height={12}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M8 1.5v9M4.5 7L8 10.5 11.5 7M2 14h12" />
      </svg>
      {label}
    </button>
  );
}
