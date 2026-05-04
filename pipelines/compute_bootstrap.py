"""Day-9 pipeline — bootstrap CIs around the Day-4 DiD δ and CARs.

For each EQDP event, this:

1. Reloads prices, market, betas, universe, latest amihud — same path as
   compute_did — and rebuilds the matched-pair panel.
2. Cluster-bootstraps the DiD δ (5,000 reps, entities with replacement).
3. Cluster-bootstraps the per-ticker mean CAR for treated and controls.
4. Upserts each metric × scope into ``bootstrap_cis``.

Usage:
    python -m pipelines.compute_bootstrap
    python -m pipelines.compute_bootstrap --event tranche_2 --reps 1000
    python -m pipelines.compute_bootstrap --dry-run
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd
import typer
from rich.console import Console

from src.bootstrap import (
    BootstrapCI,
    cluster_bootstrap_did,
    cluster_bootstrap_mean_car,
)
from src.constants import (
    BENCHMARK_CAPM,
    BOOTSTRAP_REPLICATIONS,
    EVENT_WINDOWS,
    EVENTS,
)
from src.db import get_supabase
from src.events import (
    build_event_panel,
    car_by_ticker,
    event_window_dates,
    stock_returns_from_prices,
)
from src.matching import FeatureRow, match_controls
from src.returns import BetaEstimate

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)

UPSERT_CHUNK = 100


# ---------- DB helpers (same logic as compute_did, deduped) ----------


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


def _load_market(client: Any) -> pd.Series:
    rows = _paginate(client, "factor_returns", "trade_date,market")
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date").sort_index()["market"].astype("float64")


def _load_prices(client: Any) -> pd.DataFrame:
    rows = _paginate(client, "prices_daily", "ticker,trade_date,adj_close")
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    # DuckDB pagination on a single-column ORDER BY can revisit tied rows.
    return df.drop_duplicates(subset=["ticker", "trade_date"], keep="first")


def _load_betas(client: Any) -> dict[str, BetaEstimate]:
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
        "ticker,sector,in_sti30,t1_flag,t2_flag,t3_flag",
    )
    return pd.DataFrame(rows)


def _load_amihud_at(
    client: Any, tickers: list[str], on_or_before: pd.Timestamp
) -> dict[str, float]:
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


def _build_panel_for_event(
    *,
    event_id: str,
    market: pd.Series,
    prices: pd.DataFrame,
    betas: dict[str, BetaEstimate],
    universe: pd.DataFrame,
    client: Any,
) -> tuple[pd.DataFrame, set[str], set[str]]:
    window = EVENT_WINDOWS.get(event_id, (-5, 20))
    cal = pd.DatetimeIndex(sorted(market.index.unique()))
    ev = event_window_dates(event_id, cal, window=window)

    all_tickers = sorted({str(r["ticker"]) for _, r in universe.iterrows()})
    amihud = _load_amihud_at(
        client, all_tickers, ev.event_date - pd.Timedelta(days=1)
    )

    treated_feats: list[FeatureRow] = []
    control_feats: list[FeatureRow] = []
    for r in universe.to_dict(orient="records"):
        tk = str(r["ticker"])
        if tk not in betas or tk not in amihud:
            continue
        row = FeatureRow(
            ticker=tk,
            sector=str(r.get("sector") or "Unknown"),
            beta=betas[tk].beta,
            amihud_60d=amihud[tk],
        )
        if r.get("in_sti30"):
            control_feats.append(row)
        elif r.get("t1_flag") or r.get("t2_flag") or r.get("t3_flag"):
            treated_feats.append(row)

    pairs = match_controls(treated_feats, control_feats, used_unique=False)
    treated_set = set(pairs.keys())
    control_set = set(pairs.values())

    panel_universe = treated_set | control_set
    panel_prices = prices[prices["ticker"].isin(panel_universe)]
    stock_returns = stock_returns_from_prices(panel_prices)
    panel = build_event_panel(
        event=ev,
        stock_returns=stock_returns,
        market_returns=market,
        betas=betas,
    )
    return panel, treated_set, control_set


# ---------- Pipeline run-tracking ----------


def _start_run(client: Any, dry_run: bool, label: str) -> str | None:
    if dry_run:
        return None
    res = client.table("pipeline_runs").insert(
        {"job_name": f"compute_bootstrap:{label}", "status": "running",
         "metrics_json": {}}
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


def _ci_to_row(ci: BootstrapCI, run_id: str | None) -> dict[str, Any]:
    return {
        "metric": ci.metric,
        "scope": ci.scope,
        "point_estimate": ci.point,
        "lower_5": ci.lower,
        "upper_95": ci.upper,
        "n_replications": ci.n_replications,
        "pipeline_run_id": run_id,
    }


@app.command()
def main(
    event: str = typer.Option("", help="Single event ID, empty = all four EVENTS."),
    reps: int = typer.Option(BOOTSTRAP_REPLICATIONS, help="Bootstrap replications."),
    dry_run: bool = typer.Option(False, "--dry-run"),
    seed: int = typer.Option(0, help="RNG seed for reproducibility."),
) -> None:
    targets = [event] if event else list(EVENTS.keys())
    bad = [e for e in targets if e not in EVENTS]
    if bad:
        console.print(f"[red]unknown event(s): {bad}[/]")
        raise typer.Exit(2)

    console.print(
        f"[bold]compute_bootstrap[/]: events={targets}  reps={reps}  "
        f"{'[yellow](DRY RUN)[/]' if dry_run else ''}"
    )

    client = get_supabase()
    label = event or "all"
    run_id = _start_run(client, dry_run, label)
    overall: dict[str, Any] = {"events": {}, "errors": [], "reps": reps}

    try:
        console.print("  loading panel inputs…")
        prices = _load_prices(client)
        market = _load_market(client)
        betas = _load_betas(client)
        universe = _load_universe(client)
        console.print(
            f"  loaded {len(prices):,} prices, {len(market):,} market days, "
            f"{len(betas)} betas, {len(universe)} tickers"
        )

        ci_rows: list[dict[str, Any]] = []
        for ev_id in targets:
            console.print(f"  → event [bold]{ev_id}[/]…")
            try:
                panel, treated_set, control_set = _build_panel_for_event(
                    event_id=ev_id,
                    market=market,
                    prices=prices,
                    betas=betas,
                    universe=universe,
                    client=client,
                )

                # 1. δ via cluster bootstrap on entities
                console.print(
                    f"    DiD bootstrap: {len(treated_set)} treated × "
                    f"{len(control_set)} controls × {reps} reps…"
                )
                did_ci = cluster_bootstrap_did(
                    panel,
                    treated=treated_set,
                    controls=control_set,
                    metric_name="did_delta",
                    scope=ev_id,
                    n_reps=reps,
                    seed=seed,
                )
                ci_rows.append(_ci_to_row(did_ci, run_id))
                console.print(
                    f"    δ = {did_ci.point:+.4f}  "
                    f"[5%, 95%] = [{did_ci.lower:+.4f}, {did_ci.upper:+.4f}]  "
                    f"({did_ci.n_replications}/{reps} reps)"
                )

                # 2. CAR(treat), CAR(ctrl), diff via ticker-level resampling
                car = car_by_ticker(panel, column="ar_capm")
                treated_cars = car.loc[car.index.isin(treated_set)]
                control_cars = car.loc[car.index.isin(control_set)]

                if not treated_cars.dropna().empty:
                    treat_ci = cluster_bootstrap_mean_car(
                        treated_cars,
                        metric_name="car_treated",
                        scope=ev_id,
                        n_reps=reps,
                        seed=seed,
                    )
                    ci_rows.append(_ci_to_row(treat_ci, run_id))
                if not control_cars.dropna().empty:
                    ctrl_ci = cluster_bootstrap_mean_car(
                        control_cars,
                        metric_name="car_control",
                        scope=ev_id,
                        n_reps=reps,
                        seed=seed,
                    )
                    ci_rows.append(_ci_to_row(ctrl_ci, run_id))

                overall["events"][ev_id] = {
                    "did_delta": did_ci.point,
                    "did_lo": did_ci.lower,
                    "did_hi": did_ci.upper,
                    "n_treated": len(treated_set),
                    "n_controls": len(control_set),
                }

            except Exception as exc:
                overall["errors"].append({"event": ev_id, "error": str(exc)[:300]})
                console.print(f"    [red]failed[/]: {exc}")

        if not dry_run and ci_rows:
            n = 0
            for i in range(0, len(ci_rows), UPSERT_CHUNK):
                chunk = ci_rows[i : i + UPSERT_CHUNK]
                client.table("bootstrap_cis").upsert(
                    chunk, on_conflict="metric,scope"
                ).execute()
                n += len(chunk)
            overall["ci_rows_written"] = n

        status = "succeeded" if not overall["errors"] else "partial"
        _finish_run(client, run_id, status=status, metrics=overall)
        console.print(
            f"[bold green]compute_bootstrap {status}[/]  "
            f"({overall.get('ci_rows_written', 0)} CI rows written, "
            f"BENCHMARK={BENCHMARK_CAPM})"
        )
    except Exception as exc:
        _finish_run(client, run_id, status="failed", metrics=overall, error=str(exc))
        console.print(f"[red]compute_bootstrap failed:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
