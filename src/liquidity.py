"""Liquidity metrics — Amihud illiquidity, turnover velocity.

Per docs/METHODOLOGY.md §6:

    Amihud_{i,t} = |R_{i,t}| / DollarVolume_{i,t}

Lower is better — same return achieved on more dollar volume = deeper market.
We report (a) the per-day ratio, (b) a 60-day rolling mean, and (c) the
change in 60-day rolling mean from a pre-event window to a post-event window
(the "liquidity rise" signal in the candidate score).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.returns import daily_returns

DEFAULT_AMIHUD_WINDOW = 60


def amihud_daily(prices: pd.DataFrame) -> pd.Series:
    """|R| / dollar_volume per trading day, indexed by date.

    Expects columns ``adj_close`` and ``dollar_volume`` (or ``volume`` —
    we'll compute dollar_volume from adj_close * volume if missing).

    Returns a Series of NaN where dollar_volume is 0 or where R is undefined
    (first row). Caller decides whether to forward-fill or drop.
    """
    if "adj_close" not in prices.columns:
        raise KeyError("prices DataFrame must have 'adj_close' column")
    rets = daily_returns(prices["adj_close"])

    if "dollar_volume" in prices.columns:
        dv = prices["dollar_volume"].astype("float64")
    elif "volume" in prices.columns:
        dv = prices["adj_close"].astype("float64") * prices["volume"].astype("float64")
    else:
        raise KeyError("prices DataFrame needs 'dollar_volume' or 'volume'")

    # Mask zero-volume days; division yields NaN there rather than inf.
    safe_dv = dv.where(dv > 0, np.nan)
    ratio = rets.abs() / safe_dv
    ratio.name = "amihud"
    return ratio


def rolling_amihud(
    amihud: pd.Series, window: int = DEFAULT_AMIHUD_WINDOW, min_periods: int | None = None
) -> pd.Series:
    """Rolling-window mean of the daily Amihud series.

    ``min_periods`` defaults to ``window // 2`` so we don't emit a value until
    we have meaningful coverage.
    """
    mp = min_periods if min_periods is not None else max(window // 2, 1)
    out = amihud.rolling(window=window, min_periods=mp).mean()
    out.name = f"amihud_{window}d"
    return out


def turnover_velocity(
    prices: pd.DataFrame, shares_outstanding: float
) -> pd.Series:
    """volume / shares_outstanding per day. Sanity comparator to Amihud."""
    if "volume" not in prices.columns:
        raise KeyError("prices DataFrame must have 'volume' column")
    if shares_outstanding <= 0:
        raise ValueError(f"shares_outstanding must be positive, got {shares_outstanding}")
    out = prices["volume"].astype("float64") / shares_outstanding
    out.name = "turnover"
    return out


def liquidity_change(
    rolling: pd.Series,
    pre_end: pd.Timestamp,
    pre_window: int,
    post_start: pd.Timestamp,
    post_window: int,
) -> float:
    """Mean of ``rolling`` over the pre window minus mean over the post window.

    Sign convention: positive value means liquidity *improved* (Amihud fell).
    Returns NaN if either window is empty.
    """
    pre = rolling.loc[
        (rolling.index <= pre_end)
        & (rolling.index >= pre_end - pd.Timedelta(days=pre_window))
    ]
    post = rolling.loc[
        (rolling.index >= post_start)
        & (rolling.index <= post_start + pd.Timedelta(days=post_window))
    ]
    if pre.empty or post.empty:
        return float("nan")
    return float(pre.mean() - post.mean())
