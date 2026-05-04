"""Decoupled candidate score — the SCREEN, not the impact estimator.

Per docs/METHODOLOGY.md §3 / docs/STRATEGY.md §4.7:

    Score = 0.30·LiquidityRise
          + 0.20·InstitutionalProxy
          + 0.15·IndexInclusion
          + 0.15·BrokerNamed
          + 0.20·FilingPresent

The single biggest mistake to avoid (CLAUDE.md):
    *Returns* — total_return, momentum, drawdown — are NOT inputs. They
    appear only on the right-hand side of the impact regression elsewhere.
    A test asserts this: holding the *flow* signals fixed, the score must
    not move when we vary the cumulative return outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.constants import SCORE_WEIGHTS


@dataclass(frozen=True, slots=True)
class TickerFeatures:
    """All five signals for one ticker, each in [0, 1] before weighting."""

    ticker: str
    liquidity_rise: float
    institutional_proxy: float
    index_inclusion: float  # 0 or 1
    broker_named: float
    filing_present: float  # 0 or 1


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Per-signal raw value + weighted total. Total ∈ [0, 1] given weights sum to 1.

    Per-signal fields hold the *raw* signal value in [0, 1] (matching the
    candidate_scores DB schema), not the post-weight contribution. ``total``
    is the weighted sum.
    """

    ticker: str
    liquidity_rise: float
    institutional_proxy: float
    index_inclusion: float
    broker_named: float
    filing_present: float
    total: float

    def as_db_row(self) -> dict[str, float | int | str]:
        return {
            "ticker": self.ticker,
            "liquidity_rise": float(self.liquidity_rise),
            "institutional_proxy": float(self.institutional_proxy),
            "index_inclusion": int(round(self.index_inclusion)),
            "broker_named": float(self.broker_named),
            "filing_present": int(round(self.filing_present)),
            "total_score": float(self.total),
        }


# ---------------------------------------------------------------------------
# Score function
# ---------------------------------------------------------------------------


def candidate_score(
    feat: TickerFeatures, weights: dict[str, float] = SCORE_WEIGHTS
) -> ScoreBreakdown:
    """Pure function: weight-and-sum the five signals.

    Each signal must be pre-normalised to [0, 1]. The function does not look
    at price, return, or volume directly — only at the upstream feature row.
    """
    if not _approximately_one(sum(weights.values())):
        raise ValueError(f"score weights must sum to 1.0, got {sum(weights.values())}")

    total = float(
        weights["liquidity_rise"] * feat.liquidity_rise
        + weights["institutional_proxy"] * feat.institutional_proxy
        + weights["index_inclusion"] * feat.index_inclusion
        + weights["broker_named"] * feat.broker_named
        + weights["filing_present"] * feat.filing_present
    )
    return ScoreBreakdown(
        ticker=feat.ticker,
        liquidity_rise=feat.liquidity_rise,
        institutional_proxy=feat.institutional_proxy,
        index_inclusion=feat.index_inclusion,
        broker_named=feat.broker_named,
        filing_present=feat.filing_present,
        total=total,
    )


def _approximately_one(x: float, tol: float = 1e-9) -> bool:
    return abs(x - 1.0) < tol


# ---------------------------------------------------------------------------
# Signal computation helpers
# ---------------------------------------------------------------------------


def rank_normalise(values: pd.Series) -> pd.Series:
    """Map a Series to [0, 1] by rank percentile.

    NaN values stay NaN. Ties get the average rank (pandas default).
    A higher original value → higher rank → score closer to 1.
    """
    if values.empty:
        return values
    ranks = values.rank(method="average", na_option="keep")
    n = ranks.notna().sum()
    if n <= 1:
        return ranks.where(ranks.isna(), 0.5)
    return (ranks - 1.0) / (n - 1.0)


def liquidity_rise_from_amihud(
    amihud_60d: pd.Series, *, pre_end: pd.Timestamp, post_start: pd.Timestamp
) -> float:
    """Mean(amihud_60d) over the pre window minus mean over the post window.

    Higher Amihud = less liquid. So pre - post > 0 means liquidity improved.
    Returns the raw delta (caller should rank-normalise across universe).
    NaN if either window is empty.
    """
    if amihud_60d.empty:
        return float("nan")
    pre = amihud_60d.loc[
        (amihud_60d.index >= pre_end - pd.Timedelta(days=90))
        & (amihud_60d.index <= pre_end)
    ]
    post = amihud_60d.loc[
        (amihud_60d.index >= post_start)
        & (amihud_60d.index <= post_start + pd.Timedelta(days=90))
    ]
    pre = pre.dropna()
    post = post.dropna()
    if pre.empty or post.empty:
        return float("nan")
    return float(pre.mean() - post.mean())


def institutional_proxy_from_prices(
    prices: pd.DataFrame, *, lookback: int = 30
) -> float:
    """Fraction of the last ``lookback`` trading days where close exceeds
    the same-day rolling 30-day VWAP.

    VWAP_t = Σ(typical_price_i · volume_i) / Σ(volume_i)  for i in [t-30, t]
    typical_price = (H + L + C) / 3.

    Returns a value in [0, 1]; higher = more sustained close-above-VWAP =
    stronger sustained-accumulation signal. NaN if too little data.
    """
    needed = {"high", "low", "close", "volume"}
    if not needed.issubset(prices.columns):
        raise KeyError(f"prices missing columns: {sorted(needed - set(prices.columns))}")
    if len(prices) < lookback + 1:
        return float("nan")

    p = prices.sort_index().copy()
    p["typical"] = (p["high"] + p["low"] + p["close"]) / 3.0
    p["pv"] = p["typical"] * p["volume"]
    rolling_pv = p["pv"].rolling(window=lookback, min_periods=lookback).sum()
    rolling_v = p["volume"].rolling(window=lookback, min_periods=lookback).sum()
    safe_v = rolling_v.where(rolling_v > 0, np.nan)
    vwap = rolling_pv / safe_v

    last = p.tail(lookback)
    last_vwap = vwap.tail(lookback)
    above = (last["close"] > last_vwap).astype(float)
    above = above.where(last_vwap.notna(), np.nan)
    valid = above.dropna()
    if valid.empty:
        return float("nan")
    return float(valid.mean())


def broker_named_normalise(broker_count: int, max_count: int) -> float:
    """Linear normalise broker_named_count to [0, 1] given the universe max."""
    if max_count <= 0:
        return 0.0
    return float(broker_count) / float(max_count)


def filing_present_within(
    filings: pd.Series, *, as_of: pd.Timestamp, months: int = 12
) -> int:
    """1 if any filing date in (as_of - months, as_of], else 0.

    ``filings`` is a Series of pd.Timestamp (filing dates) for one ticker.
    """
    if filings.empty:
        return 0
    cutoff = as_of - pd.DateOffset(months=months)
    return int(((filings > cutoff) & (filings <= as_of)).any())
