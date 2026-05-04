"""Day-3 tests — Amihud illiquidity ratio with toy fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.liquidity import (
    amihud_daily,
    liquidity_change,
    rolling_amihud,
    turnover_velocity,
)


def _toy_prices(n: int = 5) -> pd.DataFrame:
    """5-day toy with hand-computable Amihud values."""
    dates = pd.bdate_range("2024-01-02", periods=n)
    return pd.DataFrame(
        {
            "adj_close": [100.0, 102.0, 100.0, 105.0, 103.0],
            "volume": [1_000_000, 2_000_000, 500_000, 1_000_000, 0],
        },
        index=dates,
    )


def test_amihud_daily_matches_hand_calculation() -> None:
    df = _toy_prices()
    a = amihud_daily(df)
    # First row has no return → NaN
    assert pd.isna(a.iloc[0])
    # Day 2: |R| = 2/100 = 0.02; dv = 102 * 2_000_000
    assert a.iloc[1] == pytest.approx(0.02 / (102.0 * 2_000_000))
    # Day 5: zero volume → NaN
    assert pd.isna(a.iloc[4])


def test_amihud_uses_dollar_volume_column_when_present() -> None:
    df = _toy_prices()
    df["dollar_volume"] = df["adj_close"] * df["volume"] * 2.0  # 2x scale
    a = amihud_daily(df)
    # Day 2: 0.02 / (102 * 2_000_000 * 2) — half the volume-derived value
    expected = 0.02 / (102.0 * 2_000_000 * 2.0)
    assert a.iloc[1] == pytest.approx(expected)


def test_amihud_requires_adj_close() -> None:
    df = pd.DataFrame({"close": [100.0, 101.0], "volume": [1, 2]})
    with pytest.raises(KeyError, match="adj_close"):
        amihud_daily(df)


def test_amihud_requires_volume_or_dollar_volume() -> None:
    df = pd.DataFrame({"adj_close": [100.0, 101.0]})
    with pytest.raises(KeyError, match="volume"):
        amihud_daily(df)


def test_rolling_amihud_window_correctness() -> None:
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2024-01-02", periods=120)
    a = pd.Series(rng.uniform(1e-9, 1e-8, size=120), index=dates, name="amihud")
    r = rolling_amihud(a, window=60)
    assert r.iloc[59] == pytest.approx(a.iloc[:60].mean())
    assert r.iloc[119] == pytest.approx(a.iloc[60:120].mean())
    # min_periods default is window//2 = 30 → first 29 values are NaN
    assert pd.isna(r.iloc[28])
    assert not pd.isna(r.iloc[29])


def test_rolling_amihud_custom_min_periods() -> None:
    a = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    r = rolling_amihud(a, window=3, min_periods=1)
    assert r.iloc[0] == 1.0
    assert r.iloc[2] == 2.0


def test_turnover_velocity_basic() -> None:
    df = _toy_prices()
    t = turnover_velocity(df, shares_outstanding=10_000_000)
    assert t.iloc[1] == pytest.approx(2_000_000 / 10_000_000)


def test_turnover_velocity_rejects_invalid_shares() -> None:
    df = _toy_prices()
    with pytest.raises(ValueError, match="positive"):
        turnover_velocity(df, shares_outstanding=0)


def test_liquidity_change_positive_means_improvement() -> None:
    """Higher Amihud = less liquid; if it falls post-event, change > 0."""
    dates = pd.bdate_range("2024-01-02", periods=200)
    pre_amihud = 1e-7
    post_amihud = 5e-8
    series = pd.Series(
        [pre_amihud] * 100 + [post_amihud] * 100, index=dates, name="amihud_60d"
    )
    delta = liquidity_change(
        series,
        pre_end=dates[99],
        pre_window=60,
        post_start=dates[100],
        post_window=60,
    )
    assert delta > 0
    assert delta == pytest.approx(pre_amihud - post_amihud, abs=1e-12)


def test_liquidity_change_returns_nan_on_empty_window() -> None:
    series = pd.Series([1.0], index=pd.DatetimeIndex(["2024-01-02"]))
    delta = liquidity_change(
        series,
        pre_end=pd.Timestamp("2020-01-01"),
        pre_window=60,
        post_start=pd.Timestamp("2030-01-01"),
        post_window=60,
    )
    assert np.isnan(delta)
