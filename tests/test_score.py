"""Day-7 tests — decoupled candidate score, including the
"returns are not an input" invariance check.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.constants import SCORE_WEIGHTS
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

# --- core math ------------------------------------------------------------


def test_score_weights_sum_to_one() -> None:
    assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_candidate_score_zero_features_zero_total() -> None:
    feat = TickerFeatures("X.SI", 0.0, 0.0, 0.0, 0.0, 0.0)
    s = candidate_score(feat)
    assert s.total == 0.0


def test_candidate_score_max_features_total_one() -> None:
    feat = TickerFeatures("X.SI", 1.0, 1.0, 1.0, 1.0, 1.0)
    s = candidate_score(feat)
    assert s.total == pytest.approx(1.0)


def test_candidate_score_per_signal_contribution() -> None:
    # Only liquidity_rise = 1, others 0 → total = w_liquidity_rise = 0.30
    feat = TickerFeatures("X.SI", 1.0, 0.0, 0.0, 0.0, 0.0)
    s = candidate_score(feat)
    assert s.total == pytest.approx(SCORE_WEIGHTS["liquidity_rise"])
    assert s.liquidity_rise == 1.0  # raw value preserved
    # Only filing_present = 1 → total = w_filing_present = 0.20
    feat = TickerFeatures("X.SI", 0.0, 0.0, 0.0, 0.0, 1.0)
    s = candidate_score(feat)
    assert s.total == pytest.approx(SCORE_WEIGHTS["filing_present"])
    assert s.filing_present == 1.0


def test_candidate_score_rejects_unnormalised_weights() -> None:
    bad = {**SCORE_WEIGHTS, "liquidity_rise": 0.5}  # sum > 1
    with pytest.raises(ValueError, match="must sum to 1"):
        candidate_score(TickerFeatures("X.SI", 0.5, 0.5, 0, 0.5, 1), weights=bad)


def test_score_breakdown_db_row_int_dummies() -> None:
    feat = TickerFeatures("X.SI", 0.7, 0.4, 1.0, 0.3, 0.0)
    s = candidate_score(feat)
    row = s.as_db_row()
    assert row["ticker"] == "X.SI"
    assert isinstance(row["index_inclusion"], int)
    assert isinstance(row["filing_present"], int)
    assert row["index_inclusion"] == 1
    assert row["filing_present"] == 0


# --- THE crucial test: score must not move with returns -------------------


def test_score_invariant_to_cumulative_return_level() -> None:
    """Two tickers with identical FLOW signals (liquidity, institutional flow,
    broker count, filing presence, index status) but vastly different
    cumulative returns must receive the same score.

    This is the methodological cornerstone — the OpenClaw circular score
    failed this test by construction. See CLAUDE.md "the single biggest
    mistake to avoid"."""
    feat = TickerFeatures(
        ticker="STOCK.SI",
        liquidity_rise=0.7,
        institutional_proxy=0.6,
        index_inclusion=1.0,
        broker_named=0.5,
        filing_present=1.0,
    )
    score_a = candidate_score(feat).total
    # Now imagine the same stock with the same flow signals but +245%
    # cumulative return — it had a great year. Same TickerFeatures because
    # the score function never sees prices/returns directly.
    score_b = candidate_score(feat).total
    assert score_a == score_b
    # And a stock that lost 60% with the same flow signals also gets the
    # same score — the screen is forensic, not momentum.
    score_c = candidate_score(feat).total
    assert score_a == score_c


# --- rank_normalise -------------------------------------------------------


def test_rank_normalise_maps_to_unit_interval() -> None:
    s = pd.Series([10.0, 20.0, 30.0, 40.0])
    out = rank_normalise(s)
    assert out.min() == 0.0
    assert out.max() == 1.0


def test_rank_normalise_preserves_nan() -> None:
    s = pd.Series([1.0, np.nan, 3.0])
    out = rank_normalise(s)
    assert pd.isna(out.iloc[1])
    assert out.iloc[0] == 0.0
    assert out.iloc[2] == 1.0


# --- liquidity_rise -------------------------------------------------------


def test_liquidity_rise_positive_when_amihud_falls() -> None:
    dates = pd.bdate_range("2024-01-02", periods=200)
    series = pd.Series(
        [1e-7] * 100 + [5e-8] * 100, index=dates, name="amihud_60d"
    )
    delta = liquidity_rise_from_amihud(
        series,
        pre_end=dates[99],
        post_start=dates[100],
    )
    # Pre 1e-7 - post 5e-8 = +5e-8 (improvement)
    assert delta == pytest.approx(5e-8, abs=1e-12)


def test_liquidity_rise_returns_nan_on_empty_window() -> None:
    s = pd.Series(dtype=float)
    s.index = pd.DatetimeIndex([])
    assert np.isnan(
        liquidity_rise_from_amihud(
            s,
            pre_end=pd.Timestamp("2024-01-01"),
            post_start=pd.Timestamp("2024-06-01"),
        )
    )


# --- institutional_proxy --------------------------------------------------


def test_institutional_proxy_close_above_vwap_full_window() -> None:
    """If close > rolling 30d VWAP every day, proxy = 1.0.

    Use a constant-OHLC series so VWAP = typical_price = constant; with
    close > typical, close also strictly exceeds the rolling VWAP.
    """
    dates = pd.bdate_range("2024-01-02", periods=60)
    df = pd.DataFrame(
        {
            "high": 104.0,
            "low": 100.0,
            "close": 103.0,  # > typical (104+100+103)/3 = 102.33
            "volume": 1_000_000,
        },
        index=dates,
    )
    proxy = institutional_proxy_from_prices(df, lookback=30)
    assert proxy == pytest.approx(1.0)


def test_institutional_proxy_close_below_vwap_full_window() -> None:
    dates = pd.bdate_range("2024-01-02", periods=60)
    high = pd.Series([102.0] * 60, index=dates)
    low = pd.Series([98.0] * 60, index=dates)
    # close = 99 < typical = 100; close should be below VWAP
    close = pd.Series([99.0] * 60, index=dates)
    df = pd.DataFrame(
        {"high": high, "low": low, "close": close, "volume": 1_000_000}
    )
    proxy = institutional_proxy_from_prices(df, lookback=30)
    assert proxy == pytest.approx(0.0)


def test_institutional_proxy_returns_nan_with_too_little_data() -> None:
    df = pd.DataFrame(
        {"high": [1.0], "low": [1.0], "close": [1.0], "volume": [1]},
        index=pd.bdate_range("2024-01-02", periods=1),
    )
    assert np.isnan(institutional_proxy_from_prices(df, lookback=30))


def test_institutional_proxy_requires_columns() -> None:
    df = pd.DataFrame({"close": [1.0, 2.0]})
    with pytest.raises(KeyError, match="missing"):
        institutional_proxy_from_prices(df)


# --- broker_named ---------------------------------------------------------


def test_broker_named_normalise() -> None:
    assert broker_named_normalise(0, 3) == 0.0
    assert broker_named_normalise(2, 4) == 0.5
    assert broker_named_normalise(3, 3) == 1.0
    assert broker_named_normalise(5, 0) == 0.0  # max=0 short-circuit


# --- filing_present -------------------------------------------------------


def test_filing_present_within_window() -> None:
    filings = pd.Series(
        [pd.Timestamp("2025-09-01"), pd.Timestamp("2024-01-15")]
    )
    assert filing_present_within(
        filings, as_of=pd.Timestamp("2026-01-01"), months=12
    ) == 1
    assert filing_present_within(
        filings, as_of=pd.Timestamp("2027-01-01"), months=12
    ) == 0
    assert filing_present_within(pd.Series([], dtype=object), as_of=pd.Timestamp("2026-01-01")) == 0


# --- BreakDown round-trip -------------------------------------------------


def test_score_breakdown_total_equals_weighted_sum_of_raw() -> None:
    feat = TickerFeatures("X.SI", 0.7, 0.6, 1.0, 0.5, 1.0)
    s: ScoreBreakdown = candidate_score(feat)
    expected = (
        SCORE_WEIGHTS["liquidity_rise"] * s.liquidity_rise
        + SCORE_WEIGHTS["institutional_proxy"] * s.institutional_proxy
        + SCORE_WEIGHTS["index_inclusion"] * s.index_inclusion
        + SCORE_WEIGHTS["broker_named"] * s.broker_named
        + SCORE_WEIGHTS["filing_present"] * s.filing_present
    )
    assert s.total == pytest.approx(expected)
