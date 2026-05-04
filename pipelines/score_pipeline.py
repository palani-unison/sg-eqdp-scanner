"""Day-7 pipeline — populate candidate_scores for one snapshot date.

Reads the gold tables already produced by Days 2-4:
    prices_daily         → institutional_proxy (close vs 30d VWAP)
    liquidity_metrics    → liquidity_rise (Δ amihud_60d pre/post tranche_2)
    tickers              → broker_named, in_next50, eqdp_tier
    filings_t1           → filing_present (within 12 months of snapshot)

Per CLAUDE.md, the score does NOT touch returns. The unit test in
tests/test_score.py asserts this directly. This pipeline composes those
pure functions over real Supabase rows.

Usage:
    python -m pipelines.score_pipeline                # snapshot = today
    python -m pipelines.score_pipeline --as-of 2026-05-01 --dry-run
"""

from __future__ import annotations

import sys
from datetime import date
from typing import Any

import pandas as pd
import typer
from rich.console import Console

from src.constants import EVENTS, TIER_CONTROL, TIER_NONE, TIER_T2, TIER_T3, event_date
from src.db import get_supabase
from src.score import (
    ScoreBreakdown,
    TickerFeatures,
    broker_named_normalise,
    candidate_score,
    filing_present_within,
    institutional_proxy_from_prices,
    liquidity_rise_from_amihud,
    rank_normalise,
)

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)

UPSERT_CHUNK = 1000


# ---------- DB helpers (paginated) ----------


def _paginate(client: Any, table: str, select: str, **filters: Any) -> list[dict[str, Any]]:
    PAGE = 1000
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        q = client.table(table).select(select)
        for k, v in filters.items():
            q = q.eq(k, v)
        order_col = "trade_date" if "trade_date" in select else "ticker"
        res = q.order(order_col).range(offset, offset + PAGE - 1).execute()
        if not res.data:
            break
        rows.extend(res.data)
        if len(res.data) < PAGE:
            break
        offset += PAGE
    return rows


def _load_universe(client: Any) -> pd.DataFrame:
    rows = _paginate(
        client,
        "tickers",
        "ticker,name,sector,broker_named_count,in_sti30,in_next50,t1_flag,t2_flag,t3_flag",
    )
    return pd.DataFrame(rows)


def _load_prices_for(client: Any, ticker: str, *, last_n_days: int = 60) -> pd.DataFrame:
    """Pull the last ~60 trading days of OHLCV needed for institutional_proxy."""
    rows: list[dict[str, Any]] = []
    PAGE = 1000
    offset = 0
    while True:
        res = (
            client.table("prices_daily")
            .select("trade_date,high,low,close,volume")
            .eq("ticker", ticker)
            .order("trade_date", desc=True)
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        if not res.data:
            break
        rows.extend(res.data)
        if len(rows) >= last_n_days * 2 or len(res.data) < PAGE:
            break
        offset += PAGE
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    return df.tail(last_n_days * 2)  # buffer for rolling 30d


def _load_amihud_for(client: Any, ticker: str) -> pd.Series:
    rows: list[dict[str, Any]] = []
    PAGE = 1000
    offset = 0
    while True:
        res = (
            client.table("liquidity_metrics")
            .select("trade_date,amihud_60d")
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
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    s = df.set_index("trade_date")["amihud_60d"].astype("float64")
    return s


def _load_filings_for(client: Any, ticker: str) -> pd.Series:
    """Filing dates as a Series for one ticker (currently empty until Day 6)."""
    res = (
        client.table("filings_t1")
        .select("filing_date")
        .eq("ticker", ticker)
        .limit(1000)
        .execute()
    )
    if not res.data:
        return pd.Series([], dtype=object)
    return pd.Series([pd.Timestamp(r["filing_date"]) for r in res.data])


# ---------- Pipeline run-tracking ----------


def _start_run(client: Any, dry_run: bool, as_of: pd.Timestamp) -> str | None:
    if dry_run:
        return None
    res = client.table("pipeline_runs").insert(
        {
            "job_name": "score_pipeline",
            "status": "running",
            "metrics_json": {"as_of": as_of.strftime("%Y-%m-%d")},
        }
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


# ---------- Tier resolution ----------


def _eqdp_tier(row: dict[Any, Any]) -> str:
    if row.get("t1_flag"):
        return "T1"
    if row.get("t3_flag"):
        return TIER_T3
    if row.get("t2_flag"):
        return TIER_T2
    if row.get("in_sti30"):
        return TIER_CONTROL
    return TIER_NONE


# ---------- Main ----------


@app.command()
def main(
    as_of: str = typer.Option(
        "today", help="ISO date for the snapshot, or 'today'."
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
    benchmark_event: str = typer.Option(
        "tranche_2",
        help="Event ID anchoring the LiquidityRise pre/post windows.",
    ),
) -> None:
    snapshot = (
        pd.Timestamp(date.today())
        if as_of == "today"
        else pd.Timestamp(as_of)
    )
    console.print(
        f"[bold]score_pipeline[/]: snapshot={snapshot.date()}  "
        f"benchmark={benchmark_event}  "
        f"{'[yellow](DRY RUN)[/]' if dry_run else ''}"
    )

    if benchmark_event not in EVENTS:
        console.print(f"[red]unknown event: {benchmark_event}[/]")
        raise typer.Exit(2)
    bench_dt = event_date(benchmark_event)

    client = get_supabase()
    run_id = _start_run(client, dry_run, snapshot)
    metrics: dict[str, Any] = {
        "as_of": snapshot.strftime("%Y-%m-%d"),
        "benchmark_event": benchmark_event,
        "tickers_scored": 0,
        "scores_written": 0,
        "tickers_skipped": [],
    }

    try:
        universe = _load_universe(client)
        if universe.empty:
            raise RuntimeError("tickers table is empty")
        max_broker = max(int(universe["broker_named_count"].fillna(0).max()), 1)
        console.print(f"  loaded {len(universe)} tickers, max broker count = {max_broker}")

        # First pass: compute raw signals per ticker.
        rows: list[dict[str, Any]] = []
        for r in universe.to_dict(orient="records"):
            tk = str(r["ticker"])
            try:
                amihud = _load_amihud_for(client, tk)
                liq_delta = liquidity_rise_from_amihud(
                    amihud,
                    pre_end=bench_dt - pd.Timedelta(days=30),
                    post_start=bench_dt + pd.Timedelta(days=30),
                )

                prices = _load_prices_for(client, tk, last_n_days=60)
                inst_proxy = (
                    institutional_proxy_from_prices(prices, lookback=30)
                    if not prices.empty
                    else float("nan")
                )

                filings = _load_filings_for(client, tk)
                filing = filing_present_within(filings, as_of=snapshot, months=12)

                rows.append(
                    {
                        "ticker": tk,
                        "liq_delta": liq_delta,
                        "institutional_proxy": (
                            float(inst_proxy)
                            if not pd.isna(inst_proxy)
                            else float("nan")
                        ),
                        "broker_named": broker_named_normalise(
                            int(r.get("broker_named_count") or 0), max_broker
                        ),
                        "index_inclusion": float(1 if r.get("in_next50") else 0),
                        "filing_present": float(filing),
                        "tier": _eqdp_tier(r),
                    }
                )
            except Exception as exc:
                metrics["tickers_skipped"].append({"ticker": tk, "error": str(exc)[:200]})
                console.print(f"  [yellow]skip {tk}[/]: {exc}")

        feat_df = pd.DataFrame(rows)
        if feat_df.empty:
            raise RuntimeError("no feature rows produced")

        # Cross-sectional rank-normalise the continuous signals.
        feat_df["liquidity_rise"] = rank_normalise(feat_df["liq_delta"]).fillna(0.0)
        feat_df["institutional_proxy"] = rank_normalise(
            feat_df["institutional_proxy"]
        ).fillna(0.0)

        # Score every row with the pure function and stage DB rows.
        score_rows: list[dict[str, Any]] = []
        for r in feat_df.to_dict(orient="records"):
            feat = TickerFeatures(
                ticker=str(r["ticker"]),
                liquidity_rise=float(r["liquidity_rise"]),
                institutional_proxy=float(r["institutional_proxy"]),
                index_inclusion=float(r["index_inclusion"]),
                broker_named=float(r["broker_named"]),
                filing_present=float(r["filing_present"]),
            )
            sb: ScoreBreakdown = candidate_score(feat)
            db_row: dict[str, Any] = dict(sb.as_db_row())
            db_row["score_date"] = snapshot.strftime("%Y-%m-%d")
            db_row["eqdp_tier"] = r["tier"]
            db_row["pipeline_run_id"] = run_id
            score_rows.append(db_row)

        metrics["tickers_scored"] = len(score_rows)

        if not dry_run:
            n = 0
            for i in range(0, len(score_rows), UPSERT_CHUNK):
                chunk = score_rows[i : i + UPSERT_CHUNK]
                client.table("candidate_scores").upsert(
                    chunk, on_conflict="ticker,score_date"
                ).execute()
                n += len(chunk)
            metrics["scores_written"] = n
        else:
            console.print(f"  would upsert {len(score_rows)} candidate scores")

        status = "succeeded" if not metrics["tickers_skipped"] else "partial"
        _finish_run(client, run_id, status=status, metrics=metrics)
        console.print(
            f"[bold green]score_pipeline {status}[/]: "
            f"{metrics['tickers_scored']} scored, "
            f"{metrics['scores_written']} written, "
            f"{len(metrics['tickers_skipped'])} skipped"
        )
    except Exception as exc:
        _finish_run(client, run_id, status="failed", metrics=metrics, error=str(exc))
        console.print(f"[red]score_pipeline failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
