"""Day-2 tests for src/data/prices.py.

We mock yfinance.download — the unit layer must not hit the network.
A separate live smoke test runs in tests/test_prices_live.py (skipped
unless ``RUN_LIVE_PRICES=1``).
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from src.data.prices import (
    WIRE_COLUMNS,
    PriceFetchError,
    fetch_prices,
)


def _synthetic_yf_multi(
    symbols: list[str],
    start: str,
    end: str,
    *,
    inject_nulls_in: str | None = None,
) -> pd.DataFrame:
    """Build the wide multi-index frame yfinance.download returns."""
    dates = pd.bdate_range(start=start, end=end, name="Date")
    rng = np.random.default_rng(42)
    arrays: list[tuple[str, str]] = []
    cols_data: dict[tuple[str, str], np.ndarray[Any, Any]] = {}
    for sym in symbols:
        base = rng.uniform(1.0, 5.0, size=len(dates)).cumsum() + 5.0
        for field in ("Open", "High", "Low", "Close", "Adj Close"):
            arr = base + rng.normal(0, 0.1, size=len(dates))
            if inject_nulls_in == sym and field == "Close":
                arr[: len(dates) // 2] = np.nan
            cols_data[(sym, field)] = arr
            arrays.append((sym, field))
        cols_data[(sym, "Volume")] = rng.integers(1_000, 1_000_000, size=len(dates))
        arrays.append((sym, "Volume"))
    cols = pd.MultiIndex.from_tuples(arrays)
    df = pd.DataFrame(cols_data, index=dates, columns=cols)
    return df


def _synthetic_yf_single(start: str, end: str) -> pd.DataFrame:
    """Single-symbol yfinance returns flat columns."""
    dates = pd.bdate_range(start=start, end=end, name="Date")
    rng = np.random.default_rng(7)
    base = rng.uniform(1.0, 5.0, size=len(dates)).cumsum() + 5.0
    df = pd.DataFrame(
        {
            "Open": base,
            "High": base + 0.2,
            "Low": base - 0.2,
            "Close": base,
            "Adj Close": base * 0.98,
            "Volume": rng.integers(1_000, 1_000_000, size=len(dates)),
        },
        index=dates,
    )
    return df


def test_fetch_prices_multi_symbol_happy_path() -> None:
    syms = ["E28.SI", "AWX.SI"]
    raw = _synthetic_yf_multi(syms, "2024-01-02", "2024-12-31")
    with mock.patch("src.data.prices._yf_download", return_value=raw):
        df = fetch_prices(syms, "2024-01-02", "2024-12-31")
    assert list(df.columns) == list(WIRE_COLUMNS)
    assert set(df["ticker"].unique()) == set(syms)
    assert df["volume"].dtype == np.int64
    assert df["fetched_at_utc"].nunique() == 1  # single batch stamp
    # Trade dates within range
    assert pd.Timestamp(df["trade_date"].min()) >= pd.Timestamp("2024-01-02")
    assert pd.Timestamp(df["trade_date"].max()) <= pd.Timestamp("2024-12-31")


def test_fetch_prices_single_symbol_flat_frame() -> None:
    raw = _synthetic_yf_single("2024-06-01", "2024-12-31")
    with mock.patch("src.data.prices._yf_download", return_value=raw):
        df = fetch_prices(["E28.SI"], "2024-06-01", "2024-12-31")
    assert (df["ticker"] == "E28.SI").all()
    assert len(df) >= 100  # ~150 trading days expected


def test_fetch_prices_rejects_empty_symbols() -> None:
    with pytest.raises(ValueError, match="empty"):
        fetch_prices([], "2024-01-01", "2024-12-31")


def test_fetch_prices_rejects_inverted_dates() -> None:
    with pytest.raises(ValueError, match="must be after"):
        fetch_prices(["E28.SI"], "2024-12-31", "2024-01-01")


def test_fetch_prices_rejects_excessive_nulls() -> None:
    syms = ["E28.SI", "AWX.SI"]
    raw = _synthetic_yf_multi(syms, "2024-01-02", "2024-12-31", inject_nulls_in="E28.SI")
    with (
        mock.patch("src.data.prices._yf_download", return_value=raw),
        pytest.raises(PriceFetchError, match="null rate"),
    ):
        fetch_prices(syms, "2024-01-02", "2024-12-31", max_null_rate=0.01)


def test_fetch_prices_rejects_empty_result() -> None:
    empty = pd.DataFrame()
    with (
        mock.patch("src.data.prices._yf_download", return_value=empty),
        pytest.raises(PriceFetchError, match="Empty result"),
    ):
        fetch_prices(["E28.SI"], "2024-01-02", "2024-12-31")


def test_fetch_prices_rejects_too_few_rows() -> None:
    # 2 days only — far below the row-count lower bound for a multi-month range.
    syms = ["E28.SI", "AWX.SI"]
    raw = _synthetic_yf_multi(syms, "2024-12-30", "2024-12-31")
    with (
        mock.patch("src.data.prices._yf_download", return_value=raw),
        pytest.raises(PriceFetchError, match="row count"),
    ):
        fetch_prices(syms, "2024-01-02", "2024-12-31", min_rows_per_year_per_symbol=200)


def test_fetch_prices_preserves_split_adjustment() -> None:
    """Where Close ≠ Adj Close (i.e., split or dividend), both columns survive
    the long-format conversion. This is the structural CapitaLand-split check
    referenced in PLAN.md (live correctness verified separately on real data)."""
    syms = ["C38U.SI"]
    raw = _synthetic_yf_single("2024-01-02", "2024-12-31")
    # Force divergence between close and adj_close on a known row
    raw["Adj Close"] = raw["Close"] * 0.5
    with mock.patch("src.data.prices._yf_download", return_value=raw):
        df = fetch_prices(syms, "2024-01-02", "2024-12-31")
    assert (df["adj_close"] - df["close"] * 0.5).abs().max() < 1e-9
