"""Day-4 tests — event window slicing and placebo dates."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.constants import EVENTS
from src.events import (
    EventWindow,
    car_by_ticker,
    event_window_dates,
    placebo_event_dates,
    stock_returns_from_prices,
)


def _trading_calendar(start: str, end: str) -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, end=end)


def test_event_window_dates_returns_aligned_offsets() -> None:
    cal = _trading_calendar("2025-07-01", "2025-08-31")
    win = event_window_dates("tranche_1", cal, window=(-1, 5))
    assert isinstance(win, EventWindow)
    assert win.event_id == "tranche_1"
    assert win.event_date == pd.Timestamp("2025-07-21")
    assert win.t_offsets[0] == -1
    assert len(win.dates) == len(win.t_offsets)
    # Event date 2025-07-21 is a Monday → trading day → t=0 is that day
    t0_pos = win.t_offsets.index(0)
    assert win.dates[t0_pos] == pd.Timestamp("2025-07-21")


def test_event_window_clipped_at_calendar_start() -> None:
    cal = _trading_calendar("2025-07-21", "2025-08-31")  # event day is first
    win = event_window_dates("tranche_1", cal, window=(-5, 5))
    # We can't go before the first day; t-offsets should start at 0
    assert win.t_offsets[0] == 0


def test_event_window_skips_weekend_event() -> None:
    cal = _trading_calendar("2026-02-01", "2026-03-31")
    # 2026-02-12 is Thursday → trading day. Pick a window that crosses weekends.
    win = event_window_dates("expansion", cal, window=(-2, 5))
    assert win.event_date == pd.Timestamp("2026-02-12")
    # No weekend dates in the result
    for d in win.dates:
        assert d.weekday() < 5


def test_placebo_event_dates_excludes_eqdp_dates() -> None:
    eqdp = {pd.Timestamp(v) for v in EVENTS.values()}
    chosen = placebo_event_dates(n=10, seed=42, year=2024)
    assert all(d not in eqdp for d in chosen)
    assert len(chosen) == 10


def test_placebo_event_dates_reproducible() -> None:
    a = placebo_event_dates(n=8, seed=7, year=2024)
    b = placebo_event_dates(n=8, seed=7, year=2024)
    assert a == b


def test_placebo_event_dates_caps_at_population() -> None:
    # Only ~52 Wednesdays in a year; asking for more returns all candidates.
    chosen = placebo_event_dates(n=10_000, seed=0, year=2024)
    assert 40 <= len(chosen) <= 60


def test_stock_returns_from_prices_round_trips() -> None:
    df = pd.DataFrame(
        {
            "ticker": ["X.SI"] * 4 + ["Y.SI"] * 4,
            "trade_date": list(pd.bdate_range("2024-01-02", periods=4)) * 2,
            "adj_close": [100, 101, 99, 105, 50, 51, 50.5, 52],
        }
    )
    out = stock_returns_from_prices(df)
    assert set(out.keys()) == {"X.SI", "Y.SI"}
    assert pd.isna(out["X.SI"].iloc[0])
    assert out["X.SI"].iloc[1] == pytest.approx(0.01)


def test_car_by_ticker_sums_correctly() -> None:
    panel = pd.DataFrame(
        {
            "ticker": ["A", "A", "A", "B", "B"],
            "t": [-1, 0, 1, 0, 1],
            "ar_capm": [0.01, 0.02, np.nan, 0.005, 0.01],
        }
    )
    car = car_by_ticker(panel, column="ar_capm")
    assert car["A"] == pytest.approx(0.03)
    assert car["B"] == pytest.approx(0.015)
