"""CAPM-adjusted abnormal returns.

Implements docs/METHODOLOGY.md §4. The contract:

    R_{i,t} = α_i + β_i · R_{market,t} + ε_{i,t}      (estimation)
    AR_{i,t} = R_{i,t} − (α_i + β_i · R_{market,t})    (test window)
    CAR_{i,[t1,t2]} = Σ AR_{i,t}

β is estimated on a 252-trading-day window ending 30 days before the event
to avoid information leakage. The estimation window and the test window are
disjoint by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.constants import CAPM_BETA_WINDOW_DAYS, CAPM_GAP_DAYS


@dataclass(frozen=True, slots=True)
class BetaEstimate:
    """Result of a single CAPM β estimation."""

    ticker: str
    window_end: pd.Timestamp
    window_days: int
    alpha: float
    beta: float
    r_squared: float
    n_obs: int

    def expected_return(self, market_return: float) -> float:
        return self.alpha + self.beta * market_return


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple daily return from an adjusted-close price series, indexed by date.

    NaN for the first row (no prior price). Float64 throughout.
    """
    if not prices.index.is_monotonic_increasing:
        prices = prices.sort_index()
    rets = prices.astype("float64").pct_change()
    rets.name = "ret"
    return rets


def estimate_beta(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    *,
    window_end: pd.Timestamp,
    window_days: int = CAPM_BETA_WINDOW_DAYS,
    gap_days: int = CAPM_GAP_DAYS,
    ticker: str | None = None,
) -> BetaEstimate:
    """Estimate (α, β, R²) on the trailing window ending ``window_end - gap_days``.

    Inputs are tz-naive return series indexed by date. Both must be aligned;
    we re-align here defensively. Raises ValueError if too few observations.
    """
    end = pd.Timestamp(window_end).tz_localize(None)
    cutoff_end = end - pd.Timedelta(days=gap_days)
    # We use calendar days for the window; trading days fall out via .reindex_like.
    cutoff_start = cutoff_end - pd.Timedelta(days=int(window_days * 1.6))

    aligned = pd.concat(
        [stock_returns.rename("y"), market_returns.rename("x")], axis=1
    ).dropna()
    aligned = aligned.loc[
        (aligned.index >= cutoff_start) & (aligned.index <= cutoff_end)
    ]
    # Take the last `window_days` trading days.
    aligned = aligned.tail(window_days)

    if len(aligned) < window_days // 2:
        raise ValueError(
            f"insufficient data for β: got {len(aligned)} obs, "
            f"need ≥{window_days // 2} for window ending {cutoff_end.date()}"
        )

    y = aligned["y"].to_numpy(dtype="float64")
    x = aligned["x"].to_numpy(dtype="float64")
    X = sm.add_constant(x)
    model = sm.OLS(y, X).fit()
    alpha_hat, beta_hat = float(model.params[0]), float(model.params[1])
    r_squared = float(model.rsquared)

    return BetaEstimate(
        ticker=ticker or "",
        window_end=end,
        window_days=window_days,
        alpha=alpha_hat,
        beta=beta_hat,
        r_squared=r_squared,
        n_obs=len(aligned),
    )


def abnormal_returns(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    estimate: BetaEstimate,
) -> pd.Series:
    """Pointwise AR_{t} = R_{i,t} − (α + β · R_{m,t})."""
    aligned = pd.concat(
        [stock_returns.rename("ri"), market_returns.rename("rm")], axis=1
    ).dropna()
    expected = estimate.alpha + estimate.beta * aligned["rm"]
    ar = aligned["ri"] - expected
    ar.name = "ar"
    return ar


def cumulative_abnormal_return(
    ar: pd.Series,
    event_date: pd.Timestamp,
    window: tuple[int, int],
) -> tuple[float, pd.Series]:
    """CAR over a [t1, t2] trading-day window relative to ``event_date``.

    Returns (CAR scalar, per-day AR series labelled by relative day t).
    Uses trading days from the AR index; if the event date is not a trading
    day, the next available trading day is treated as t = 0.
    """
    if not ar.index.is_monotonic_increasing:
        ar = ar.sort_index()
    event = pd.Timestamp(event_date).tz_localize(None)
    # Find the first trading day ≥ event_date as t=0
    on_or_after = ar.index[ar.index >= event]
    if len(on_or_after) == 0:
        raise ValueError(f"no trading days on or after {event.date()} in AR series")
    t0 = on_or_after[0]
    t0_idx = int(np.flatnonzero(ar.index == t0)[0])

    t1, t2 = window
    lo = max(t0_idx + t1, 0)
    hi = min(t0_idx + t2 + 1, len(ar))
    slice_ = ar.iloc[lo:hi].copy()
    slice_.index = pd.RangeIndex(start=t1, stop=t1 + len(slice_), name="t")
    return float(slice_.sum()), slice_


def market_adjusted_returns(
    stock_returns: pd.Series, market_returns: pd.Series
) -> pd.Series:
    """Phase-1 baseline: AR = R_i − R_market (no β scaling)."""
    aligned = pd.concat(
        [stock_returns.rename("ri"), market_returns.rename("rm")], axis=1
    ).dropna()
    out = aligned["ri"] - aligned["rm"]
    out.name = "ar_mkt"
    return out
