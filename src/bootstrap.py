"""Block-bootstrap confidence intervals.

Per docs/METHODOLOGY.md §10. Two estimators:

    cluster_bootstrap_did     — for DiD δ (resample entities with replacement)
    stationary_bootstrap      — for time-series metrics (mean block length 5d)

Both return a ``BootstrapCI(point, lower, upper, n_replications)`` triple.
Default: 5,000 replications, 5–95 percentile interval.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.constants import BOOTSTRAP_BLOCK_LENGTH, BOOTSTRAP_REPLICATIONS
from src.matching import did_panel


@dataclass(frozen=True, slots=True)
class BootstrapCI:
    """Point estimate plus a percentile confidence interval."""

    metric: str
    scope: str
    point: float
    lower: float
    upper: float
    n_replications: int
    lower_pct: float = 5.0
    upper_pct: float = 95.0


# ---------------------------------------------------------------------------
# Cluster (entity) bootstrap for DiD
# ---------------------------------------------------------------------------


def cluster_bootstrap_did(
    panel: pd.DataFrame,
    *,
    treated: set[str],
    controls: set[str],
    metric_name: str,
    scope: str,
    n_reps: int = BOOTSTRAP_REPLICATIONS,
    event_t0: int = 0,
    outcome: str = "ret",
    lower_pct: float = 5.0,
    upper_pct: float = 95.0,
    seed: int = 0,
) -> BootstrapCI:
    """Cluster-bootstrap δ from a Treated × Post DiD on the panel.

    Resamples *entities* (tickers) with replacement, preserving the within-
    entity time series. Treated and control sets are sampled separately so
    the treated/control mix is preserved. Refits ``did_panel`` each rep.

    Returns the point estimate (full-sample δ) plus the bootstrap percentile
    CI from the resampled distribution.
    """
    rng = np.random.default_rng(seed)
    treated_arr = np.array(sorted(treated))
    controls_arr = np.array(sorted(controls))
    if len(treated_arr) == 0 or len(controls_arr) == 0:
        raise ValueError("treated or controls set is empty")

    # Point estimate from the full sample
    point_res = did_panel(
        panel, treated=set(treated_arr), controls=set(controls_arr),
        event_t0=event_t0, outcome=outcome,
    )
    point = float(point_res.delta)

    # Pre-index the panel by ticker for fast slicing
    panel_idx = panel.set_index("ticker", drop=False).sort_index()
    deltas: list[float] = []

    for _ in range(n_reps):
        t_sample = rng.choice(treated_arr, size=len(treated_arr), replace=True)
        c_sample = rng.choice(controls_arr, size=len(controls_arr), replace=True)

        # Build resampled panel; preserve replicated entities by suffixing
        frames = []
        new_treated: set[str] = set()
        new_controls: set[str] = set()
        for j, tk in enumerate(t_sample):
            sub = panel_idx.loc[[tk]].copy()
            new_id = f"{tk}__t{j}"
            sub["ticker"] = new_id
            frames.append(sub)
            new_treated.add(new_id)
        for j, tk in enumerate(c_sample):
            sub = panel_idx.loc[[tk]].copy()
            new_id = f"{tk}__c{j}"
            sub["ticker"] = new_id
            frames.append(sub)
            new_controls.add(new_id)
        boot = pd.concat(frames, ignore_index=True)

        try:
            res = did_panel(
                boot,
                treated=new_treated,
                controls=new_controls,
                event_t0=event_t0,
                outcome=outcome,
            )
            deltas.append(float(res.delta))
        except Exception:
            continue

    if not deltas:
        raise RuntimeError("all bootstrap reps failed; check input data")
    arr = np.array(deltas)
    lo = float(np.percentile(arr, lower_pct))
    hi = float(np.percentile(arr, upper_pct))
    return BootstrapCI(
        metric=metric_name,
        scope=scope,
        point=point,
        lower=lo,
        upper=hi,
        n_replications=len(deltas),
        lower_pct=lower_pct,
        upper_pct=upper_pct,
    )


# ---------------------------------------------------------------------------
# Stationary (time-series) bootstrap
# ---------------------------------------------------------------------------


def stationary_bootstrap(
    series: pd.Series | np.ndarray,
    fn: Callable[[np.ndarray], float],
    *,
    metric_name: str,
    scope: str,
    n_reps: int = BOOTSTRAP_REPLICATIONS,
    mean_block_len: int = BOOTSTRAP_BLOCK_LENGTH,
    lower_pct: float = 5.0,
    upper_pct: float = 95.0,
    seed: int = 0,
) -> BootstrapCI:
    """Politis–Romano stationary bootstrap on a 1-D series.

    Block lengths are i.i.d. Geometric(1/mean_block_len); start indices are
    uniform on [0, n). For each rep, resample of length n is built by
    concatenating blocks (wrapping at the end), then ``fn`` is evaluated.
    """
    if isinstance(series, pd.Series):
        x = series.to_numpy(dtype="float64")
    else:
        x = np.asarray(series, dtype="float64")
    n = len(x)
    if n < 2:
        raise ValueError("series too short for bootstrap")

    rng = np.random.default_rng(seed)
    p = 1.0 / max(mean_block_len, 1)
    point = float(fn(x))
    estimates = np.empty(n_reps, dtype="float64")

    for r in range(n_reps):
        sample = np.empty(n, dtype="float64")
        i = 0
        while i < n:
            start = int(rng.integers(0, n))
            block_len = int(rng.geometric(p))
            block_len = min(block_len, n - i)
            for k in range(block_len):
                sample[i + k] = x[(start + k) % n]
            i += block_len
        estimates[r] = fn(sample)

    return BootstrapCI(
        metric=metric_name,
        scope=scope,
        point=point,
        lower=float(np.percentile(estimates, lower_pct)),
        upper=float(np.percentile(estimates, upper_pct)),
        n_replications=n_reps,
        lower_pct=lower_pct,
        upper_pct=upper_pct,
    )


# ---------------------------------------------------------------------------
# Mean CAR bootstrap (cluster on ticker)
# ---------------------------------------------------------------------------


def cluster_bootstrap_mean_car(
    car_by_ticker: pd.Series,
    *,
    metric_name: str,
    scope: str,
    n_reps: int = BOOTSTRAP_REPLICATIONS,
    lower_pct: float = 5.0,
    upper_pct: float = 95.0,
    seed: int = 0,
) -> BootstrapCI:
    """Bootstrap the mean of per-ticker CARs by resampling tickers with
    replacement. Faster path than full DiD bootstrap; same idea."""
    arr = car_by_ticker.dropna().to_numpy(dtype="float64")
    if len(arr) == 0:
        raise ValueError("car_by_ticker is empty after dropna")
    rng = np.random.default_rng(seed)
    point = float(arr.mean())
    n = len(arr)
    means = np.empty(n_reps, dtype="float64")
    for r in range(n_reps):
        idx = rng.integers(0, n, size=n)
        means[r] = arr[idx].mean()
    return BootstrapCI(
        metric=metric_name,
        scope=scope,
        point=point,
        lower=float(np.percentile(means, lower_pct)),
        upper=float(np.percentile(means, upper_pct)),
        n_replications=n_reps,
        lower_pct=lower_pct,
        upper_pct=upper_pct,
    )
