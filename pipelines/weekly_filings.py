"""Weekly pipeline — pull substantial-shareholder filings from SGXNet,
resolve to EQDP managers, dedupe, upsert ``filings_t1``, and flip the
``t1_flag`` on every ticker that now has at least one confirmed filing.

Operational status:
    Live SGX fetch is **deferred** (SGX's announcement portal is a JS SPA
    that needs Playwright; see scrapers/sgxnet/fetcher.py docstring).
    Until then, this pipeline runs in **fixture mode**:

        python -m pipelines.weekly_filings --fixtures-dir data/sgxnet

    Drop pre-saved filing HTML files into the fixtures directory; the
    pipeline replays them through the parser and writes to Supabase exactly
    as the live path eventually will.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import typer
from rich.console import Console

from scrapers.sgxnet.fetcher import fetch_from_fixture_dir, parse_fetched
from scrapers.sgxnet.manager_aliases import resolve_manager
from src.db import get_supabase

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)


def _start_run(client: Any, dry_run: bool) -> str | None:
    if dry_run:
        return None
    res = client.table("pipeline_runs").insert(
        {"job_name": "weekly_filings", "status": "running", "metrics_json": {}}
    ).execute()
    return str(res.data[0]["run_id"])


def _finish_run(
    client: Any, run_id: str | None, *, status: str, metrics: dict[str, Any],
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


@app.command()
def main(
    fixtures_dir: str = typer.Option(
        "",
        help="Path to a directory of pre-saved SGX filing HTML files. "
        "Required until live fetch is wired.",
    ),
    live: bool = typer.Option(
        False, "--live",
        help="Use live SGX scraper. Currently raises NotImplementedError.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    if live and fixtures_dir:
        console.print("[red]choose either --live or --fixtures-dir, not both[/]")
        raise typer.Exit(2)
    if not live and not fixtures_dir:
        console.print(
            "[yellow]No source given.[/] Pass --fixtures-dir <path> for offline "
            "ingest, or --live (NotImplementedError until Playwright is wired)."
        )
        raise typer.Exit(2)

    client = get_supabase()
    run_id = _start_run(client, dry_run)
    metrics: dict[str, Any] = {
        "fetched": 0,
        "parsed": 0,
        "matched_to_eqdp_manager": 0,
        "upserted": 0,
        "tickers_t1_flagged": 0,
        "errors": [],
    }

    try:
        if live:
            from scrapers.sgxnet.fetcher import fetch_live  # noqa: F401
            raise NotImplementedError(
                "Live SGX scrape needs Playwright. See "
                "scrapers/sgxnet/fetcher.py:fetch_live for the wiring plan."
            )

        path = Path(fixtures_dir)
        if not path.exists():
            console.print(f"[red]fixtures dir does not exist: {path}[/]")
            raise typer.Exit(2)

        rows: list[dict[str, Any]] = []
        flagged_tickers: set[str] = set()

        items = list(fetch_from_fixture_dir(path))
        metrics["fetched"] = len(items)
        console.print(f"  fetched {len(items)} filing HTML files")

        for filing in parse_fetched(iter(items)):
            metrics["parsed"] += 1
            match = resolve_manager(filing.notifier_raw)
            if not match:
                continue
            metrics["matched_to_eqdp_manager"] += 1
            rows.append(
                {
                    "filing_id": filing.filing_id,
                    "manager_id": match.manager_id,
                    "ticker": filing.ticker,
                    "effective_date": filing.effective_date,
                    "filing_date": filing.filing_date,
                    "stake_pct": filing.stake_pct,
                    "direction": filing.direction,
                    "source_url": filing.source_url,
                    "pipeline_run_id": run_id,
                }
            )
            flagged_tickers.add(filing.ticker)

        if not dry_run and rows:
            for i in range(0, len(rows), 500):
                client.table("filings_t1").upsert(
                    rows[i : i + 500], on_conflict="filing_id"
                ).execute()
            metrics["upserted"] = len(rows)

            # Flip t1_flag on every ticker we just saw a filing for.
            for tk in flagged_tickers:
                client.table("tickers").update({"t1_flag": True}).eq(
                    "ticker", tk
                ).execute()
            metrics["tickers_t1_flagged"] = len(flagged_tickers)

        status = "succeeded"
        _finish_run(client, run_id, status=status, metrics=metrics)
        console.print(
            f"[bold green]weekly_filings {status}[/]: "
            f"fetched={metrics['fetched']}, parsed={metrics['parsed']}, "
            f"EQDP-matched={metrics['matched_to_eqdp_manager']}, "
            f"upserted={metrics['upserted']}, "
            f"tickers flagged T1={metrics['tickers_t1_flagged']}"
        )
    except NotImplementedError as exc:
        _finish_run(client, run_id, status="failed", metrics=metrics, error=str(exc))
        console.print(f"[yellow]weekly_filings (deferred):[/] {exc}")
        sys.exit(2)
    except Exception as exc:
        _finish_run(client, run_id, status="failed", metrics=metrics, error=str(exc))
        console.print(f"[red]weekly_filings failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
