"""Phase 0 — laptop backfill.

Run once to populate Supabase with 5 years of OHLCV across the bootstrap
universe. Per CLAUDE.md, ``pipelines/backfill.py`` is just ``daily_score.py``
with a wider window — but Day 2 only delivers the price ingest piece. Score
recomputation lands on Day 3+.

Usage:
    python -m pipelines.backfill --start 2020-01-01 --end yesterday
    python -m pipelines.backfill --start 2024-01-01 --end 2024-12-31 --limit 5 --dry-run
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from typing import Any

import pandas as pd
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from src.constants import EQDP_MANAGER_TRANCHE, EQDP_MANAGERS
from src.data.prices import fetch_prices
from src.db import get_supabase
from src.universe import all_tickers

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)

# Tune these for memory/HTTP-payload balance. Supabase REST upserts in
# chunks of ~1000 rows reliably; yfinance batch downloads scale to ~50
# tickers per HTTP round-trip before reliability degrades.
PRICE_FETCH_BATCH = 50
UPSERT_CHUNK = 1000


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _resolve_end(end: str) -> str:
    return _yesterday() if end == "yesterday" else end


def _seed_tickers(client: Any, run_id: str | None) -> int:
    """Upsert universe rows into the ``tickers`` table. FK prereq for
    prices_daily, candidate_scores, etc."""
    rows: list[dict[str, Any]] = []
    for t in all_tickers():
        rows.append(
            {
                "ticker": t.symbol,
                "name": t.name,
                "sector": t.sector,
                "in_sti30": t.in_control,
                "t1_flag": t.in_t1,
                "t2_flag": t.in_t2,
                "t3_flag": t.in_t3,
                "broker_named_count": len(t.sources),
                "pipeline_run_id": run_id,
            }
        )
    client.table("tickers").upsert(rows, on_conflict="ticker").execute()
    return len(rows)


def _seed_managers(client: Any) -> int:
    rows = [
        {
            "manager_id": name.lower().replace(" ", "_"),
            "canonical_name": name,
            "tranche": EQDP_MANAGER_TRANCHE[name],
        }
        for name in EQDP_MANAGERS
    ]
    client.table("eqdp_managers").upsert(rows, on_conflict="manager_id").execute()
    return len(rows)


def _start_run(client: Any, *, dry_run: bool) -> str | None:
    if dry_run:
        return None
    res = (
        client.table("pipeline_runs")
        .insert(
            {
                "job_name": "backfill",
                "status": "running",
                "metrics_json": {},
            }
        )
        .execute()
    )
    return str(res.data[0]["run_id"])


def _finish_run(
    client: Any,
    run_id: str | None,
    *,
    status: str,
    metrics: dict[str, Any],
    error: str | None = None,
) -> None:
    if run_id is None:
        return
    client.table("pipeline_runs").update(
        {
            "status": status,
            "completed_at": pd.Timestamp.utcnow().isoformat(),
            "metrics_json": metrics,
            "error_message": error,
        }
    ).eq("run_id", run_id).execute()


def _upsert_prices(client: Any, df: pd.DataFrame, run_id: str | None) -> int:
    if df.empty:
        return 0
    df = df.copy()
    df["pipeline_run_id"] = run_id
    df["trade_date"] = df["trade_date"].astype(str)  # Postgres date wire format
    df = df.drop(columns=["fetched_at_utc"])  # not in prices_daily schema
    # dollar_volume was a generated column in the legacy Postgres schema;
    # the DuckDB schema stores it as a regular column, so populate it here.
    df["dollar_volume"] = df["adj_close"] * df["volume"]
    rows = df.to_dict(orient="records")
    n_written = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i : i + UPSERT_CHUNK]
        client.table("prices_daily").upsert(
            chunk, on_conflict="ticker,trade_date"
        ).execute()
        n_written += len(chunk)
    return n_written


def _chunked(seq: list[str], n: int) -> list[list[str]]:
    return [seq[i : i + n] for i in range(0, len(seq), n)]


@app.command()
def main(
    start: str = typer.Option(..., help="ISO date, e.g. 2020-01-01"),
    end: str = typer.Option("yesterday", help="ISO date or 'yesterday'"),
    limit: int = typer.Option(0, help="Limit number of tickers (smoke test). 0 = all."),
    dry_run: bool = typer.Option(False, "--dry-run", help="No DB writes."),
    skip_seed: bool = typer.Option(False, help="Skip tickers/managers upsert."),
) -> None:
    end_resolved = _resolve_end(end)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end_resolved)
    if end_ts <= start_ts:
        console.print(f"[red]end {end_ts.date()} must be after start {start_ts.date()}[/]")
        raise typer.Exit(2)

    universe = all_tickers()
    if limit > 0:
        universe = universe[:limit]
    symbols = [t.symbol for t in universe]
    console.print(
        f"[bold]backfill[/]: {len(symbols)} tickers x "
        f"{(end_ts - start_ts).days} days "
        f"({start_ts.date()} -> {end_ts.date()})  "
        f"{'[yellow](DRY RUN)[/]' if dry_run else ''}"
    )

    if dry_run:
        console.print(
            f"  would seed {len(universe)} tickers + {len(EQDP_MANAGERS)} managers"
        )
        console.print(
            f"  would batch-fetch {len(_chunked(symbols, PRICE_FETCH_BATCH))} "
            f"yfinance request(s)"
        )
        console.print("[yellow]dry-run: nothing executed.[/]")
        return

    client = get_supabase()
    run_id = _start_run(client, dry_run=dry_run)
    metrics: dict[str, Any] = {
        "symbols": len(symbols),
        "start": start_ts.isoformat(),
        "end": end_ts.isoformat(),
        "rows_upserted": 0,
        "tickers_seeded": 0,
        "managers_seeded": 0,
        "fetch_batches": 0,
        "fetch_failures": [],
    }

    try:
        if not skip_seed:
            metrics["tickers_seeded"] = _seed_tickers(client, run_id)
            metrics["managers_seeded"] = _seed_managers(client)
            console.print(
                f"  seeded {metrics['tickers_seeded']} tickers, "
                f"{metrics['managers_seeded']} managers"
            )

        batches = _chunked(symbols, PRICE_FETCH_BATCH)
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("fetching prices", total=len(batches))
            for batch in batches:
                try:
                    df = fetch_prices(batch, start_ts, end_ts)
                    n = _upsert_prices(client, df, run_id)
                    metrics["rows_upserted"] += n
                    metrics["fetch_batches"] += 1
                except Exception as exc:
                    metrics["fetch_failures"].append(
                        {"symbols": batch, "error": str(exc)[:300]}
                    )
                    console.print(
                        f"  [red]batch failed[/] ({len(batch)} symbols): {exc}"
                    )
                progress.update(task, advance=1)

        status = "succeeded" if not metrics["fetch_failures"] else "partial"
        _finish_run(client, run_id, status=status, metrics=metrics)
        console.print(
            f"[bold green]backfill {status}[/]: "
            f"{metrics['rows_upserted']:,} rows across "
            f"{metrics['fetch_batches']} batch(es), "
            f"{len(metrics['fetch_failures'])} failure(s)"
        )
    except Exception as exc:
        _finish_run(client, run_id, status="failed", metrics=metrics, error=str(exc))
        console.print(f"[red]backfill failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
