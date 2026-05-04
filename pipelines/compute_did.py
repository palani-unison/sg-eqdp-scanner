"""Day-4 pipeline — event windows + matched-pair DiD per EQDP event.

For each event in EVENTS, this:

1. Loads prices, market returns, and the latest CAPM β estimate per ticker.
2. Builds the event panel using the EVENT_WINDOWS defaults.
3. Splits the universe into:
       - treated   = tickers whose row in `tickers` has T1, T2, or T3 = true
       - controls  = STI-30 (`in_sti30 = true`)
4. Matches each treated stock to its closest STI-30 control on
   (sector, β, amihud_60d). Falls back to the global pool when no
   same-sector control exists.
5. Runs PanelOLS DiD with entity + time FE on the matched pair panel.
6. Upserts AR rows into ``abnormal_returns`` (one row per ticker × event ×
   t × benchmark), and the per-event δ summary into ``pipeline_runs.metrics_json``.

Usage:
    python -m pipelines.compute_did                     # all 4 events
    python -m pipelines.compute_did --event tranche_1   # one event
    python -m pipelines.compute_did --dry-run
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd
import typer
from rich.console import Console

from src.constants import (
    BENCHMARK_CAPM,
    EVENT_WINDOWS,
    EVENTS,
)
from src.events import (
    build_event_panel,
    car_by_ticker,
    event_window_dates,
    stock_returns_from_prices,
)
from src.matching import DiDResult, FeatureRow, did_panel, match_controls
from src.returns import BetaEstimate

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)

UPSERT_CHUNK = 1000


# --- DB helpers ------------------------------------------------------------


def _start_run(client: Any, dry_run: bool, label: str) -> str | None:
    if dry_run:
        return None
    res = client.table("pipeline_runs").insert(
        {"job_name": f"compute_did:{label}", "status": "running", "metrics_json": {}}
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


def _paginate(client: Any, table: str, select: str, **filters: Any) -> list[dict[str, Any]]:
    PAGE = 1000
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        q = client.table(table).select(select)
        for k, v in filters.items():
            q = q.eq(k, v)
        res = q.order("trade_date" if "trade_date" in select else "ticker").range(
            offset, offset + PAGE - 1
        ).execute()
        if not res.data:
            break
        rows.extend(res.data)
        if len(res.data) < PAGE:
            break
        offset += PAGE
    return rows


def _load_market_returns(client: Any) -> pd.Series:
    rows = _paginate(client, "factor_returns", "trade_date,market")
    if not rows:
        raise RuntimeError("factor_returns is empty — run compute_metrics first")
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    s = df.set_index("trade_date").sort_index()["market"].astype("float64")
    s.name = "market"
    return s


def _load_all_prices(client: Any) -> pd.DataFrame:
    rows = _paginate(client, "prices_daily", "ticker,trade_date,adj_close")
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    # DuckDB pagination on a single-column ORDER BY can revisit rows when ties
    # exist (one trade_date appears across many tickers). The (ticker, trade_date)
    # primary key guarantees uniqueness — drop any duplicate pairs from paging.
    return df.drop_duplicates(subset=["ticker", "trade_date"], keep="first")


def _load_latest_betas(client: Any) -> dict[str, BetaEstimate]:
    """Return {ticker: BetaEstimate} for the most recent window_end per ticker."""
    rows = _paginate(
        client, "betas", "ticker,window_end,window_days,alpha,beta,r_squared"
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return {}
    df = df.sort_values(["ticker", "window_end"], ascending=[True, False])
    df = df.drop_duplicates("ticker", keep="first")
    out: dict[str, BetaEstimate] = {}
    for r in df.to_dict(orient="records"):
        out[str(r["ticker"])] = BetaEstimate(
            ticker=str(r["ticker"]),
            window_end=pd.Timestamp(r["window_end"]),
            window_days=int(r["window_days"]),
            alpha=float(r["alpha"]),
            beta=float(r["beta"]),
            r_squared=float(r["r_squared"]),
            n_obs=0,
        )
    return out


def _load_universe(client: Any) -> pd.DataFrame:
    rows = _paginate(
        client,
        "tickers",
        "ticker,name,sector,in_sti30,t1_flag,t2_flag,t3_flag",
    )
    return pd.DataFrame(rows)


def _load_amihud_60d_at(
    client: Any, tickers: list[str], on_or_before: pd.Timestamp
) -> dict[str, float]:
    """Latest non-null amihud_60d per ticker, on or before ``on_or_before``."""
    out: dict[str, float] = {}
    iso = on_or_before.strftime("%Y-%m-%d")
    for tk in tickers:
        res = (
            client.table("liquidity_metrics")
            .select("amihud_60d,trade_date")
            .eq("ticker", tk)
            .lte("trade_date", iso)
            .order("trade_date", desc=True)
            .limit(50)
            .execute()
        )
        for row in res.data:
            v = row.get("amihud_60d")
            if v is not None:
                out[tk] = float(v)
                break
    return out


def _build_features(
    universe: pd.DataFrame,
    betas: dict[str, BetaEstimate],
    amihud: dict[str, float],
) -> tuple[list[FeatureRow], list[FeatureRow]]:
    """Split universe into (treated, control) feature rows."""
    treated: list[FeatureRow] = []
    controls: list[FeatureRow] = []
    for r in universe.to_dict(orient="records"):
        tk = str(r["ticker"])
        if tk not in betas or tk not in amihud:
            continue  # missing β or liquidity → skip
        row = FeatureRow(
            ticker=tk,
            sector=str(r.get("sector") or "Unknown"),
            beta=betas[tk].beta,
            amihud_60d=amihud[tk],
        )
        if r.get("in_sti30"):
            controls.append(row)
        elif r.get("t1_flag") or r.get("t2_flag") or r.get("t3_flag"):
            treated.append(row)
    return treated, controls


# --- AR upsert -------------------------------------------------------------


def _ar_rows_from_panel(
    panel: pd.DataFrame, event_id: str, run_id: str | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    panel_sorted = panel.sort_values(["ticker", "t"])
    car_running: dict[str, float] = {}
    for r in panel_sorted.to_dict(orient="records"):
        tk = str(r["ticker"])
        ar = r.get("ar_capm")
        if ar is None or pd.isna(ar):
            continue
        car_running[tk] = car_running.get(tk, 0.0) + float(ar)
        out.append(
            {
                "ticker": tk,
                "event_id": event_id,
                "t": int(r["t"]),
                "benchmark": BENCHMARK_CAPM,
                "ar": float(ar),
                "car": car_running[tk],
                "pipeline_run_id": run_id,
            }
        )
    return out


def _upsert_ar(client: Any, rows: list[dict[str, Any]]) -> int:
    n = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i : i + UPSERT_CHUNK]
        client.table("abnormal_returns").upsert(
            chunk, on_conflict="ticker,event_id,t,benchmark"
        ).execute()
        n += len(chunk)
    return n


# --- Main loop -------------------------------------------------------------


def _process_event(
    *,
    event_id: str,
    market: pd.Series,
    prices: pd.DataFrame,
    betas: dict[str, BetaEstimate],
    universe: pd.DataFrame,
    client: Any,
    run_id: str | None,
    dry_run: bool,
    amihud_cache: dict[str, dict[str, float]],
) -> dict[str, Any]:
    window = EVENT_WINDOWS.get(event_id, (-5, 20))
    cal = pd.DatetimeIndex(sorted(market.index.unique()))
    ev_window = event_window_dates(event_id, cal, window=window)

    # Fetch amihud_60d on the day before the event for matching
    if event_id not in amihud_cache:
        all_tickers = sorted({str(r["ticker"]) for _, r in universe.iterrows()})
        amihud_cache[event_id] = _load_amihud_60d_at(
            client, all_tickers, ev_window.event_date - pd.Timedelta(days=1)
        )
    amihud = amihud_cache[event_id]

    treated_feats, control_feats = _build_features(universe, betas, amihud)
    if not treated_feats or not control_feats:
        return {
            "event_id": event_id,
            "skipped": "no treated or no controls after feature filtering",
            "treated": len(treated_feats),
            "controls": len(control_feats),
        }

    pairs = match_controls(treated_feats, control_feats, used_unique=False)
    treated_set = set(pairs.keys())
    control_set = set(pairs.values())

    # Build panel only for the matched pair set
    panel_universe = treated_set | control_set
    panel_prices = prices[prices["ticker"].isin(panel_universe)]
    stock_returns = stock_returns_from_prices(panel_prices)

    panel = build_event_panel(
        event=ev_window,
        stock_returns=stock_returns,
        market_returns=market,
        betas=betas,
    )

    # Programme-level CAR, treated vs controls
    car = car_by_ticker(panel, column="ar_capm")
    treated_car = car.loc[car.index.isin(treated_set)].mean()
    control_car = car.loc[car.index.isin(control_set)].mean()

    # DiD on raw returns with entity + time FE
    try:
        result: DiDResult = did_panel(
            panel,
            treated=treated_set,
            controls=control_set,
            event_t0=0,
            outcome="ret",
        )
    except Exception as exc:
        result = None  # type: ignore[assignment]
        did_error = str(exc)[:200]
    else:
        did_error = ""

    metrics: dict[str, Any] = {
        "event_id": event_id,
        "window": list(window),
        "treated_n": len(treated_set),
        "controls_n": len(control_set),
        "panel_rows": len(panel),
        "treated_car_mean": (
            float(treated_car) if not pd.isna(treated_car) else None
        ),
        "control_car_mean": (
            float(control_car) if not pd.isna(control_car) else None
        ),
        "did_delta": result.delta if result else None,
        "did_se": result.std_error if result else None,
        "did_t": result.t_stat if result else None,
        "did_p": result.p_value if result else None,
        "did_error": did_error,
    }

    if not dry_run:
        ar_rows = _ar_rows_from_panel(panel, event_id, run_id)
        metrics["ar_rows_written"] = _upsert_ar(client, ar_rows)
    else:
        metrics["ar_rows_written"] = 0

    return metrics


@app.command()
def main(
    event: str = typer.Option(
        "", help="Single event ID to process; empty = all four EVENTS."
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    from src.db import get_supabase

    client = get_supabase()
    targets = [event] if event else list(EVENTS.keys())
    bad = [e for e in targets if e not in EVENTS]
    if bad:
        console.print(f"[red]unknown event(s): {bad}[/]")
        raise typer.Exit(2)

    label = event or "all"
    run_id = _start_run(client, dry_run, label)
    overall: dict[str, Any] = {"events": {}, "errors": []}

    try:
        console.print("  loading prices, market, betas, universe…")
        prices = _load_all_prices(client)
        market = _load_market_returns(client)
        betas = _load_latest_betas(client)
        universe = _load_universe(client)
        console.print(
            f"  loaded {len(prices):,} prices, {len(market):,} market days, "
            f"{len(betas)} betas, {len(universe)} tickers"
        )

        amihud_cache: dict[str, dict[str, float]] = {}
        for ev in targets:
            console.print(f"  → event [bold]{ev}[/]…")
            try:
                m = _process_event(
                    event_id=ev,
                    market=market,
                    prices=prices,
                    betas=betas,
                    universe=universe,
                    client=client,
                    run_id=run_id,
                    dry_run=dry_run,
                    amihud_cache=amihud_cache,
                )
                overall["events"][ev] = m
                console.print(
                    f"    treated={m['treated_n']} controls={m['controls_n']}  "
                    f"CAR(treat)={m.get('treated_car_mean')}  "
                    f"CAR(ctrl)={m.get('control_car_mean')}  "
                    f"δ={m.get('did_delta')}  p={m.get('did_p')}  "
                    f"AR rows={m['ar_rows_written']}"
                )
            except Exception as exc:
                overall["errors"].append({"event": ev, "error": str(exc)[:300]})
                console.print(f"    [red]failed[/]: {exc}")

        status = "succeeded" if not overall["errors"] else "partial"
        _finish_run(client, run_id, status=status, metrics=overall)
        console.print(f"[bold green]compute_did {status}[/]")
    except Exception as exc:
        _finish_run(client, run_id, status="failed", metrics=overall, error=str(exc))
        console.print(f"[red]compute_did failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
