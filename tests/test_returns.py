"""Day-3 tests — CAPM β, AR, CAR using toy fixtures (no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.returns import (
    BetaEstimate,
    abnormal_returns,
    cumulative_abnormal_return,
    daily_returns,
    estimate_beta,
    market_adjusted_returns,
)


def _toy_returns(
    n: int,
    *,
    beta: float,
    alpha: float = 0.0,
    sigma: float = 0.0,
    seed: int = 0,
) -> tuple[pd.Series, pd.Series]:
    """Construct (stock_ret, market_ret) where stock = α + β·market + ε."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n, name="date")
    market_arr = rng.normal(0, 0.01, size=n)
    market = pd.Series(market_arr, index=dates, name="rm")
    eps = rng.normal(0, sigma, size=n) if sigma > 0 else np.zeros(n)
    stock = pd.Series(alpha + beta * market_arr + eps, index=dates, name="ri")
    return stock, market


def test_daily_returns_matches_pct_change() -> None:
    prices = pd.Series(
        [100.0, 101.0, 99.99, 105.0],
        index=pd.bdate_range("2024-01-02", periods=4),
    )
    rets = daily_returns(prices)
    assert pd.isna(rets.iloc[0])
    assert rets.iloc[1] == pytest.approx(0.01)
    assert rets.iloc[2] == pytest.approx((99.99 - 101.0) / 101.0)


def test_estimate_beta_recovers_known_beta_no_noise() -> None:
    stock, market = _toy_returns(400, beta=1.5, alpha=0.0001, sigma=0.0)
    # Pick window_end after the data ends so the trailing 252 days fit inside.
    window_end = stock.index[-1] + pd.Timedelta(days=60)
    est = estimate_beta(
        stock,
        market,
        window_end=window_end,
        window_days=252,
        gap_days=30,
        ticker="TOY",
    )
    assert est.beta == pytest.approx(1.5, abs=1e-9)
    assert est.alpha == pytest.approx(0.0001, abs=1e-9)
    assert est.r_squared == pytest.approx(1.0, abs=1e-9)
    assert est.ticker == "TOY"
    assert est.n_obs == 252


def test_estimate_beta_recovers_with_small_noise() -> None:
    stock, market = _toy_returns(400, beta=0.8, sigma=0.001)
    window_end = stock.index[-1] + pd.Timedelta(days=60)
    est = estimate_beta(stock, market, window_end=window_end, gap_days=30)
    assert est.beta == pytest.approx(0.8, abs=0.05)
    assert est.r_squared > 0.9


def test_estimate_beta_raises_on_too_few_obs() -> None:
    stock, market = _toy_returns(50, beta=1.0)
    with pytest.raises(ValueError, match="insufficient data"):
        estimate_beta(
            stock, market, window_end=pd.Timestamp("2024-01-01"), window_days=252
        )


def test_abnormal_returns_zero_when_data_matches_model() -> None:
    stock, market = _toy_returns(400, beta=1.2, alpha=0.0002, sigma=0.0)
    window_end = stock.index[-1] + pd.Timedelta(days=60)
    est = estimate_beta(stock, market, window_end=window_end)
    ar = abnormal_returns(stock, market, est)
    assert ar.abs().max() < 1e-12


def test_abnormal_returns_isolates_stock_specific_shock() -> None:
    stock, market = _toy_returns(400, beta=1.0, sigma=0.0)
    # Inject a +5% shock on a single day inside the estimation window
    shock_date = stock.index[100]
    stock.loc[shock_date] += 0.05
    # Estimate β on data BEFORE the shock so the model isn't fit to it.
    pre_shock_end = stock.index[80]
    window_end = pre_shock_end + pd.Timedelta(days=31)
    # Need fewer obs than 252 since pre_shock window is short — use 60-day β.
    est = estimate_beta(
        stock, market, window_end=window_end, window_days=60, gap_days=30
    )
    ar = abnormal_returns(stock, market, est)
    assert ar.loc[shock_date] == pytest.approx(0.05, abs=1e-3)


def test_cumulative_abnormal_return_sums_window() -> None:
    dates = pd.bdate_range("2024-01-02", periods=20)
    ar = pd.Series(np.full(20, 0.01), index=dates, name="ar")
    car, slice_ = cumulative_abnormal_return(
        ar, event_date=dates[10], window=(-2, 5)
    )
    assert car == pytest.approx(0.01 * 8, abs=1e-12)
    assert slice_.index[0] == -2
    assert slice_.index[-1] == 5


def test_cumulative_abnormal_return_handles_event_off_calendar() -> None:
    dates = pd.bdate_range("2024-01-02", periods=20)
    ar = pd.Series(np.arange(20, dtype=float) * 0.001, index=dates)
    # Event on Saturday — should skip to Monday (next bdate)
    saturday = dates[5] + pd.Timedelta(days=1)
    car, slice_ = cumulative_abnormal_return(ar, event_date=saturday, window=(0, 1))
    # Next trading day after the saturday is the next bdate in dates
    assert slice_.iloc[0] == ar.loc[ar.index >= saturday].iloc[0]


def test_market_adjusted_baseline() -> None:
    stock, market = _toy_returns(50, beta=1.5, sigma=0.0)
    out = market_adjusted_returns(stock, market)
    # AR_market = R_i - R_m = (1.5 - 1) * R_m
    assert (out / market).iloc[1:].mean() == pytest.approx(0.5, abs=1e-9)


def test_beta_estimate_expected_return() -> None:
    est = BetaEstimate(
        ticker="X",
        window_end=pd.Timestamp("2024-01-01"),
        window_days=252,
        alpha=0.0001,
        beta=1.2,
        r_squared=0.85,
        n_obs=252,
    )
    assert est.expected_return(0.01) == pytest.approx(0.0001 + 1.2 * 0.01)
