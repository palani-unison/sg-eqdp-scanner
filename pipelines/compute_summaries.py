"""Compute pre-rolled summary tables that the web app reads.

Populates two tables:

    ticker_summaries     — one row per ticker with car_total, volume_lift_pct,
                           amihud_change. Drives the beneficiary scatter chart.

    cohort_timeseries    — one row per trading day with treatment_cum,
                           control_cum, sti_cum (cumulative log-returns). Drives
                           the treatment-vs-control-vs-STI line chart.

Inputs:
    prices_daily, abnormal_returns, factor_returns, tickers, liquidity_metrics

Usage:
    python -m pipelines.compute_summaries
    python -m pipelines.compute_summaries --dry-run
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import pandas as pd
import typer
from rich.console import Console

from src.constants import EVENTS, event_date
from src.db import get_supabase

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)
UPSERT_CHUNK = 500


def _paginate(client: Any, table: str, select: str, **filters: Any) -> list[dict[str, Any]]:
    PAGE = 1000  # noqa: N806
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


def _start_run(client: Any, dry_run: bool) -> str | None:
    if dry_run:
        return None
    res = client.table("pipeline_runs").insert(
        {"job_name": "compute_summaries", "status": "running", "metrics_json": {}}
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


def _compute_ticker_summaries(
    client: Any,
    universe: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """Per-ticker CAR sum + average volume-lift across the four EQDP events."""
    # CAR per ticker per event = car at the LAST t in the window for that
    # (ticker, event_id) row in abnormal_returns.
    ar_rows = _paginate(client, "abnormal_returns", "ticker,event_id,t,car",
                        benchmark="capm")
    ar_df = pd.DataFrame(ar_rows) if ar_rows else pd.DataFrame()
    if ar_df.empty:
        car_per_ticker_event = pd.DataFrame(columns=["ticker", "event_id", "car"])
    else:
        # last-t per (ticker, event)
        ar_df = ar_df.sort_values(["ticker", "event_id", "t"])
        car_per_ticker_event = (
            ar_df.groupby(["ticker", "event_id"], as_index=False)
            .agg(car=("car", "last"))
        )
    car_total = car_per_ticker_event.groupby("ticker", as_index=False).agg(
        car_total=("car", "sum"),
        car_mean=("car", "mean"),
        n_events=("event_id", "nunique"),
    )

    # Volume lift per ticker = mean across events of (post60d_avg / pre60d_avg) - 1
    prices = prices.copy()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    lifts: dict[str, list[float]] = {}
    for ev_id in EVENTS:
        ev_dt = event_date(ev_id)
        pre_lo = ev_dt - pd.Timedelta(days=90)
        pre_hi = ev_dt - pd.Timedelta(days=1)
        post_lo = ev_dt + pd.Timedelta(days=1)
        post_hi = ev_dt + pd.Timedelta(days=90)
        sub_pre = prices[
            (prices["trade_date"] >= pre_lo)
            & (prices["trade_date"] <= pre_hi)
        ]
        sub_post = prices[
            (prices["trade_date"] >= post_lo)
            & (prices["trade_date"] <= post_hi)
        ]
        pre_v = sub_pre.groupby("ticker")["volume"].mean()
        post_v = sub_post.groupby("ticker")["volume"].mean()
        joined = pd.concat([pre_v.rename("pre"), post_v.rename("post")], axis=1).dropna()
        lift = (joined["post"] / joined["pre"]) - 1.0
        lift = lift.replace([np.inf, -np.inf], np.nan).dropna()
        for tk, val in lift.items():
            lifts.setdefault(str(tk), []).append(float(val))

    vol_lift = pd.DataFrame(
        [
            {"ticker": tk, "volume_lift_pct": float(np.mean(vs))}
            for tk, vs in lifts.items()
            if vs
        ]
    )

    summary = car_total.merge(vol_lift, on="ticker", how="outer")
    summary = universe[["ticker"]].merge(summary, on="ticker", how="left")
    summary["amihud_change"] = None  # placeholder; filled in next iteration
    return summary


def _compute_cohort_timeseries(
    universe: pd.DataFrame,
    prices: pd.DataFrame,
    sti: pd.Series,
    *,
    baseline_date: pd.Timestamp,
) -> pd.DataFrame:
    """Per-day cumulative log-return for treatment cohort, control cohort, STI."""
    treated = set(universe[(universe.get("t1_flag", False)) |
                           (universe.get("t2_flag", False)) |
                           (universe.get("t3_flag", False))]["ticker"])
    control = set(universe[universe.get("in_sti30", False)]["ticker"])

    px = prices.copy()
    px["trade_date"] = pd.to_datetime(px["trade_date"])
    px = px.sort_values(["ticker", "trade_date"])
    px = px[px["trade_date"] >= baseline_date]

    # Daily simple returns per ticker
    px["ret"] = px.groupby("ticker")["adj_close"].pct_change()

    # Mean simple return across cohort each day, then cumulative log
    def cohort_cum(tickers: set[str]) -> pd.Series:
        sub = px[px["ticker"].isin(tickers)]
        if sub.empty:
            return pd.Series(dtype=float)
        daily_mean = sub.groupby("trade_date")["ret"].mean()
        # Convert to cumulative log return
        return np.log(1.0 + daily_mean.fillna(0)).cumsum()

    t_cum = cohort_cum(treated)
    c_cum = cohort_cum(control)

    # STI cumulative log return from same baseline
    sti_aligned = sti.copy()
    sti_aligned.index = pd.to_datetime(sti_aligned.index)
    sti_aligned = sti_aligned.loc[sti_aligned.index >= baseline_date]
    sti_cum = np.log(1.0 + sti_aligned.fillna(0).astype("float64")).cumsum()

    frames = []
    if not t_cum.empty:
        frames.append(t_cum.rename("treatment_cum"))
    if not c_cum.empty:
        frames.append(c_cum.rename("control_cum"))
    if not sti_cum.empty:
        frames.append(sti_cum.rename("sti_cum"))
    if not frames:
        return pd.DataFrame(
            columns=[
                "trade_date", "treatment_cum", "control_cum", "sti_cum",
                "n_treatment", "n_control",
            ]
        )
    out = pd.concat(frames, axis=1).dropna(how="all")
    out.index = pd.to_datetime(out.index)
    out["n_treatment"] = len(treated)
    out["n_control"] = len(control)
    out = out.reset_index().rename(columns={"index": "trade_date"})
    return out


def _upsert(client: Any, table: str, rows: list[dict[str, Any]], on_conflict: str) -> int:
    n = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i : i + UPSERT_CHUNK]
        client.table(table).upsert(chunk, on_conflict=on_conflict).execute()
        n += len(chunk)
    return n


@app.command()
def main(
    baseline: str = typer.Option("2024-01-02", help="Baseline date for cumulative-return charts."),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    client = get_supabase()
    run_id = _start_run(client, dry_run)
    metrics: dict[str, Any] = {
        "baseline": baseline,
        "ticker_summary_rows": 0,
        "cohort_rows": 0,
    }

    try:
        console.print("  loading inputs…")
        universe = pd.DataFrame(
            _paginate(client, "tickers",
                      "ticker,t1_flag,t2_flag,t3_flag,in_sti30")
        )
        prices_rows = _paginate(client, "prices_daily",
                                "ticker,trade_date,adj_close,volume")
        prices = pd.DataFrame(prices_rows)
        factor_rows = _paginate(client, "factor_returns", "trade_date,market")
        sti = pd.DataFrame(factor_rows)
        sti["trade_date"] = pd.to_datetime(sti["trade_date"])
        sti_series = sti.set_index("trade_date")["market"].astype("float64")

        console.print(
            f"    {len(universe)} tickers, {len(prices):,} prices, "
            f"{len(sti_series):,} STI days"
        )

        # 1. Ticker summaries (CAR + volume lift per ticker)
        ticker_df = _compute_ticker_summaries(client, universe, prices)
        ticker_rows = []
        for r in ticker_df.to_dict(orient="records"):
            ticker_rows.append(
                {
                    "ticker": r["ticker"],
                    "car_total": (
                        float(r["car_total"]) if pd.notna(r.get("car_total")) else None
                    ),
                    "car_mean": (
                        float(r["car_mean"]) if pd.notna(r.get("car_mean")) else None
                    ),
                    "volume_lift_pct": (
                        float(r["volume_lift_pct"])
                        if pd.notna(r.get("volume_lift_pct"))
                        else None
                    ),
                    "amihud_change": None,
                    "n_events": (
                        int(r["n_events"]) if pd.notna(r.get("n_events")) else 0
                    ),
                    "pipeline_run_id": run_id,
                }
            )
        if not dry_run:
            metrics["ticker_summary_rows"] = _upsert(
                client, "ticker_summaries", ticker_rows, on_conflict="ticker"
            )
        console.print(f"    ticker_summaries: {len(ticker_rows)} rows")

        # 2. Cohort timeseries (treat / ctrl / STI cumulative log-return)
        baseline_dt = pd.Timestamp(baseline)
        cohort_df = _compute_cohort_timeseries(
            universe, prices, sti_series, baseline_date=baseline_dt
        )
        cohort_rows = []
        for r in cohort_df.to_dict(orient="records"):
            cohort_rows.append(
                {
                    "trade_date": pd.Timestamp(r["trade_date"]).strftime("%Y-%m-%d"),
                    "treatment_cum": (
                        float(r["treatment_cum"])
                        if pd.notna(r.get("treatment_cum"))
                        else None
                    ),
                    "control_cum": (
                        float(r["control_cum"])
                        if pd.notna(r.get("control_cum"))
                        else None
                    ),
                    "sti_cum": (
                        float(r["sti_cum"]) if pd.notna(r.get("sti_cum")) else None
                    ),
                    "n_treatment": int(r["n_treatment"]),
                    "n_control": int(r["n_control"]),
                    "pipeline_run_id": run_id,
                }
            )
        if not dry_run:
            metrics["cohort_rows"] = _upsert(
                client, "cohort_timeseries", cohort_rows, on_conflict="trade_date"
            )
        console.print(f"    cohort_timeseries: {len(cohort_rows)} rows")

        _finish_run(client, run_id, status="succeeded", metrics=metrics)
        console.print(
            f"[bold green]compute_summaries succeeded[/]: "
            f"{metrics['ticker_summary_rows']} ticker rows, "
            f"{metrics['cohort_rows']} cohort rows"
        )
    except Exception as exc:  # noqa: BLE001
        _finish_run(client, run_id, status="failed", metrics=metrics, error=str(exc))
        console.print(f"[red]compute_summaries failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
