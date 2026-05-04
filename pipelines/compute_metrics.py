"""Day-3 pipeline — compute CAPM β + Amihud over the existing prices_daily.

Per docs/PLAN.md Day 3: populate ``betas`` and ``liquidity_metrics`` for the
tickers we have prices for, using the announcement-event window ending
``EVENTS['announcement'] - CAPM_GAP_DAYS`` and a 252-trading-day estimation
window (defaults from src/constants.py).

Also fetches the STI index for the same date range and writes daily market
returns to ``factor_returns``. (SMB / HML come later — Day 9 robustness.)

Usage:
    python -m pipelines.compute_metrics                   # full run
    python -m pipelines.compute_metrics --dry-run         # no writes
    python -m pipelines.compute_metrics --limit 5         # smoke test
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd
import typer
from rich.console import Console

from src.constants import (
    BENCHMARK_CAPM,
    CAPM_BETA_WINDOW_DAYS,
    CAPM_GAP_DAYS,
    STI_TICKER,
    event_date,
)
from src.data.prices import fetch_prices
from src.db import get_supabase
from src.liquidity import amihud_daily, rolling_amihud
from src.returns import daily_returns, estimate_beta

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)

UPSERT_CHUNK = 1000


def _start_run(client: Any, dry_run: bool) -> str | None:
    if dry_run:
        return None
    res = client.table("pipeline_runs").insert(
        {"job_name": "compute_metrics", "status": "running", "metrics_json": {}}
    ).execute()
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


def _fetch_market_returns(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch ^STI prices and return daily returns indexed by tz-naive Timestamp."""
    df = fetch_prices(
        [STI_TICKER],
        start,
        end,
        max_null_rate=0.10,
        min_rows_per_year_per_symbol=180,
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").set_index("trade_date")
    return daily_returns(df["adj_close"])


def _upsert_factor_returns(
    client: Any, market: pd.Series, run_id: str | None
) -> int:
    rows = []
    for dt, val in market.dropna().items():
        rows.append(
            {
                "trade_date": pd.Timestamp(str(dt)).strftime("%Y-%m-%d"),
                "market": float(val),
                "pipeline_run_id": run_id,
            }
        )
    n = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        client.table("factor_returns").upsert(
            rows[i : i + UPSERT_CHUNK], on_conflict="trade_date"
        ).execute()
        n += len(rows[i : i + UPSERT_CHUNK])
    return n


def _load_ticker_prices(client: Any, ticker: str) -> pd.DataFrame:
    """Pull all prices_daily rows for a ticker, sorted by trade_date.

    PostgREST max_rows is 1000 server-side; paginate via .range() until empty.
    """
    rows: list[dict[str, Any]] = []
    PAGE = 1000
    offset = 0
    while True:
        res = (
            client.table("prices_daily")
            .select("trade_date, adj_close, volume, dollar_volume")
            .eq("ticker", ticker)
            .order("trade_date")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        if not res.data:
            break
        rows.extend(res.data)
        if len(res.data) < PAGE:
            break
        offset += PAGE

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    return df


def _list_tickers_with_prices(client: Any) -> list[str]:
    """Tickers that actually have rows in prices_daily."""
    res = (
        client.table("tickers")
        .select("ticker")
        .order("ticker")
        .limit(1000)
        .execute()
    )
    all_tickers = [r["ticker"] for r in res.data]
    # Filter to those with at least one price row — cheap per-ticker count.
    out: list[str] = []
    for t in all_tickers:
        cnt = (
            client.table("prices_daily")
            .select("trade_date", count="exact")
            .eq("ticker", t)
            .limit(0)
            .execute()
            .count
        )
        if cnt and cnt > 0:
            out.append(t)
    return out


def _upsert_betas(client: Any, rows: list[dict[str, Any]]) -> int:
    n = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i : i + UPSERT_CHUNK]
        client.table("betas").upsert(
            chunk, on_conflict="ticker,window_end"
        ).execute()
        n += len(chunk)
    return n


def _upsert_liquidity(client: Any, rows: list[dict[str, Any]]) -> int:
    n = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i : i + UPSERT_CHUNK]
        client.table("liquidity_metrics").upsert(
            chunk, on_conflict="ticker,trade_date"
        ).execute()
        n += len(chunk)
    return n


@app.command()
def main(
    limit: int = typer.Option(0, help="Limit number of tickers (smoke test). 0 = all."),
    dry_run: bool = typer.Option(False, "--dry-run"),
    benchmark_event: str = typer.Option(
        "announcement", help="Event ID whose date defines the β window end."
    ),
) -> None:
    bench = event_date(benchmark_event)
    console.print(
        f"[bold]compute_metrics[/]: β window ends {(bench - pd.Timedelta(days=CAPM_GAP_DAYS)).date()}, "
        f"length {CAPM_BETA_WINDOW_DAYS}d  "
        f"{'[yellow](DRY RUN)[/]' if dry_run else ''}"
    )

    client = get_supabase()
    run_id = _start_run(client, dry_run)
    metrics: dict[str, Any] = {
        "benchmark_event": benchmark_event,
        "betas_written": 0,
        "liquidity_rows_written": 0,
        "factor_rows_written": 0,
        "tickers_processed": 0,
        "tickers_failed": [],
    }

    try:
        # 1. Market returns from ^STI for the same date range as our prices.
        date_range = client.table("prices_daily").select(
            "trade_date"
        ).order("trade_date").limit(1).execute().data
        if not date_range:
            console.print("[red]prices_daily is empty — run backfill first[/]")
            raise typer.Exit(2)
        start_dt = pd.Timestamp(date_range[0]["trade_date"])
        end_dt = pd.Timestamp(client.table("prices_daily").select(
            "trade_date"
        ).order("trade_date", desc=True).limit(1).execute().data[0]["trade_date"])

        console.print(f"  fetching ^STI {start_dt.date()} → {end_dt.date()}…")
        market = _fetch_market_returns(start_dt, end_dt + pd.Timedelta(days=1))
        console.print(f"  market returns: {len(market.dropna())} obs")

        if not dry_run:
            metrics["factor_rows_written"] = _upsert_factor_returns(
                client, market, run_id
            )

        # 2. Tickers with price data.
        tickers = _list_tickers_with_prices(client)
        if limit > 0:
            tickers = tickers[:limit]
        console.print(f"  processing {len(tickers)} tickers")

        beta_rows: list[dict[str, Any]] = []
        liq_rows: list[dict[str, Any]] = []

        for tk in tickers:
            try:
                df = _load_ticker_prices(client, tk)
                if df.empty:
                    continue

                # CAPM β estimation
                stock_ret = daily_returns(df["adj_close"])
                est = estimate_beta(
                    stock_ret,
                    market,
                    window_end=bench,
                    ticker=tk,
                )
                beta_rows.append(
                    {
                        "ticker": tk,
                        "window_end": est.window_end.strftime("%Y-%m-%d"),
                        "window_days": est.window_days,
                        "alpha": est.alpha,
                        "beta": est.beta,
                        "r_squared": est.r_squared,
                        "pipeline_run_id": run_id,
                    }
                )

                # Amihud
                amihud = amihud_daily(df)
                amihud_60 = rolling_amihud(amihud, window=60)
                merged = pd.concat(
                    {"amihud": amihud, "amihud_60d": amihud_60}, axis=1
                )
                merged = merged.dropna(subset=["amihud"])
                for dt, row in merged.iterrows():
                    liq_rows.append(
                        {
                            "ticker": tk,
                            "trade_date": pd.Timestamp(str(dt)).strftime("%Y-%m-%d"),
                            "amihud": float(row["amihud"]),
                            "amihud_60d": (
                                None
                                if pd.isna(row["amihud_60d"])
                                else float(row["amihud_60d"])
                            ),
                            "pipeline_run_id": run_id,
                        }
                    )
                metrics["tickers_processed"] += 1
            except Exception as exc:
                metrics["tickers_failed"].append(
                    {"ticker": tk, "error": str(exc)[:300]}
                )
                console.print(f"  [yellow]skip {tk}:[/] {exc}")

        # The benchmark column is required by abnormal_returns table only;
        # for betas we just store one row per (ticker, window_end). The
        # benchmark info lives implicitly in the row's window_days/method.
        # Tag benchmark in metrics for traceability.
        metrics["benchmark"] = BENCHMARK_CAPM

        if not dry_run:
            metrics["betas_written"] = _upsert_betas(client, beta_rows)
            metrics["liquidity_rows_written"] = _upsert_liquidity(client, liq_rows)
        else:
            console.print(
                f"  would upsert {len(beta_rows)} betas, "
                f"{len(liq_rows)} liquidity rows"
            )

        status = "succeeded" if not metrics["tickers_failed"] else "partial"
        _finish_run(client, run_id, status=status, metrics=metrics)
        console.print(
            f"[bold green]compute_metrics {status}[/]: "
            f"{metrics['betas_written']} betas, "
            f"{metrics['liquidity_rows_written']:,} liquidity rows, "
            f"{len(metrics['tickers_failed'])} failure(s)"
        )
    except Exception as exc:
        _finish_run(client, run_id, status="failed", metrics=metrics, error=str(exc))
        console.print(f"[red]compute_metrics failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
