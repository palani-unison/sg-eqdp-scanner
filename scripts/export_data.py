"""Export every analytical Supabase table to ``data/exports/<table>.csv``.

Use this when you want the underlying data outside of Supabase — for backup,
offline analysis, or peer review. ``data/exports/`` is gitignored so the
files stay local.

Usage:
    python -m scripts.export_data
    python -m scripts.export_data --tables prices_daily,candidate_scores
    python -m scripts.export_data --out /tmp/eqdp-snapshot
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import typer
from rich.console import Console

from src.db import get_supabase

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)

# Order matters: foreign-key parents first.
DEFAULT_TABLES: list[str] = [
    "tickers",
    "eqdp_managers",
    "factor_returns",
    "prices_daily",
    "betas",
    "liquidity_metrics",
    "abnormal_returns",
    "bootstrap_cis",
    "candidate_scores",
    "ticker_summaries",
    "cohort_timeseries",
    "filings_t1",
    "synthetic_controls",
    "placebo_results",
    "pipeline_runs",
]


def _paginate_table(client: Any, table: str) -> list[dict[str, Any]]:
    """Stream every row of ``table`` via PostgREST .range() pagination."""
    PAGE = 1000  # noqa: N806
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        res = client.table(table).select("*").range(offset, offset + PAGE - 1).execute()
        data = res.data or []
        if not data:
            break
        rows.extend(data)
        if len(data) < PAGE:
            break
        offset += PAGE
    return rows


@app.command()
def main(
    out: str = typer.Option("data/exports", help="Output directory for CSV files."),
    tables: str = typer.Option(
        "",
        help="Comma-separated list of tables to export. Empty = all known analytical tables.",
    ),
) -> None:
    target = [t.strip() for t in tables.split(",") if t.strip()] or DEFAULT_TABLES
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = get_supabase()
    summary: list[tuple[str, int, str]] = []
    for table in target:
        try:
            rows = _paginate_table(client, table)
        except Exception as exc:  # noqa: BLE001 — record per-table failure
            console.print(f"  [red]{table}: failed[/] — {exc}")
            summary.append((table, 0, f"failed: {exc}"))
            continue

        path = out_dir / f"{table}.csv"
        if rows:
            pd.DataFrame(rows).to_csv(path, index=False)
        else:
            # Still write an empty file with a header line so downstream
            # tooling sees the table exists; just no data yet.
            pd.DataFrame().to_csv(path, index=False)

        size = path.stat().st_size
        console.print(
            f"  [green]✓[/] {table:22s} {len(rows):>8,} rows  →  {path}  ({size:,} bytes)"
        )
        summary.append((table, len(rows), str(path)))

    console.print()
    console.print(f"[bold]Wrote {len(summary)} tables to {out_dir}[/]")
    total_rows = sum(n for _, n, _ in summary)
    console.print(f"  total rows exported: {total_rows:,}")


if __name__ == "__main__":
    app()
