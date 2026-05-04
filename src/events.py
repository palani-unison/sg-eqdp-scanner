"""Event-window slicing + panel construction.

Per docs/PLAN.md Day 4 + docs/METHODOLOGY.md §4. The two responsibilities:

1. ``event_window_dates`` — given an event ID and a (t1, t2) trading-day
   window, return the list of actual trading days that fall in that window.

2. ``build_event_panel`` — long DataFrame indexed by (ticker, t) with raw
   return, market return, AR (CAPM), and AR (market-adjusted) columns. This
   is the input shape ``linearmodels.PanelOLS`` expects for DiD.

Also exposes ``placebo_event_dates`` for the placebo runner (Day 5).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from src.constants import (
    EVENT_WINDOWS,
    EVENTS,
    event_date,
)
from src.returns import BetaEstimate, abnormal_returns, daily_returns

# Wednesdays during 2024 used as candidate placebo dates.
_PLACEBO_YEAR: Final[int] = 2024


@dataclass(frozen=True, slots=True)
class EventWindow:
    """A trading-day window around an event, with t-aligned dates."""

    event_id: str
    event_date: pd.Timestamp
    t_offsets: tuple[int, ...]
    dates: tuple[pd.Timestamp, ...]

    def __post_init__(self) -> None:
        if len(self.t_offsets) != len(self.dates):
            raise ValueError(
                f"t_offsets ({len(self.t_offsets)}) and dates "
                f"({len(self.dates)}) must align"
            )


def event_window_dates(
    event_id: str,
    trading_days: pd.DatetimeIndex,
    window: tuple[int, int] | None = None,
) -> EventWindow:
    """Return the trading-day calendar slice [t1, t2] around ``event_id``.

    ``trading_days`` is the calendar to project against (typically the index
    of ``factor_returns`` or any one ticker's price history). If the event
    falls on a non-trading day, the next trading day becomes t = 0.
    """
    if window is None:
        window = EVENT_WINDOWS.get(event_id, (-5, 20))

    ev = event_date(event_id)
    after = trading_days[trading_days >= ev]
    if len(after) == 0:
        raise ValueError(f"no trading days on/after event {ev.date()}")
    t0 = after[0]
    t0_idx = int(np.flatnonzero(trading_days == t0)[0])

    t1, t2 = window
    lo = max(t0_idx + t1, 0)
    hi = min(t0_idx + t2 + 1, len(trading_days))
    dates = trading_days[lo:hi]
    # Offsets are relative to t0; if we clipped from below, the first offset
    # is `lo - t0_idx` (>= t1), not the requested t1.
    actual_start = lo - t0_idx
    offsets = tuple(range(actual_start, actual_start + len(dates)))
    return EventWindow(
        event_id=event_id,
        event_date=ev,
        t_offsets=offsets,
        dates=tuple(pd.Timestamp(d) for d in dates),
    )


def build_event_panel(
    *,
    event: EventWindow,
    stock_returns: dict[str, pd.Series],
    market_returns: pd.Series,
    betas: dict[str, BetaEstimate],
) -> pd.DataFrame:
    """Long DataFrame with one row per (ticker, t) inside the event window.

    Columns:
        ticker, t, trade_date, ret, market_ret, ar_capm, ar_mkt
    """
    rows: list[dict[str, object]] = []
    dates_set = list(event.dates)
    offsets_by_date = dict(zip(event.dates, event.t_offsets, strict=True))

    market_in = market_returns.loc[market_returns.index.isin(dates_set)]

    for ticker, stock_ret in stock_returns.items():
        ar_capm = (
            abnormal_returns(stock_ret, market_returns, betas[ticker])
            if ticker in betas
            else None
        )
        for d in event.dates:
            ri = stock_ret.get(d, np.nan)
            rm = market_in.get(d, np.nan)
            if pd.isna(ri) and pd.isna(rm):
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "t": offsets_by_date[d],
                    "trade_date": pd.Timestamp(d),
                    "ret": float(ri) if not pd.isna(ri) else np.nan,
                    "market_ret": float(rm) if not pd.isna(rm) else np.nan,
                    "ar_capm": (
                        float(ar_capm.get(d, np.nan))
                        if ar_capm is not None and d in ar_capm.index
                        else np.nan
                    ),
                    "ar_mkt": (
                        float(ri - rm) if not (pd.isna(ri) or pd.isna(rm)) else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def car_by_ticker(panel: pd.DataFrame, *, column: str = "ar_capm") -> pd.Series:
    """Sum AR over the event window per ticker. NaN-safe (skipna=True)."""
    if column not in panel.columns:
        raise KeyError(f"panel has no column {column!r}")
    return panel.groupby("ticker")[column].sum(min_count=1)


def placebo_event_dates(
    n: int = 20,
    *,
    year: int = _PLACEBO_YEAR,
    seed: int = 0,
    weekday: int = 2,  # Wednesday
    excluded: Iterable[pd.Timestamp] = (),
) -> list[pd.Timestamp]:
    """Sample ``n`` Wednesdays from ``year`` excluding the four EQDP dates and
    any caller-supplied exclusions. Reproducible given the same seed."""
    cal = pd.bdate_range(f"{year}-01-01", f"{year}-12-31")
    weds = [d for d in cal if d.weekday() == weekday]

    excl_set: set[pd.Timestamp] = {pd.Timestamp(d) for d in excluded}
    excl_set.update(pd.Timestamp(v) for v in EVENTS.values())
    candidates = [d for d in weds if d not in excl_set]

    rng = np.random.default_rng(seed)
    if n > len(candidates):
        return [pd.Timestamp(d) for d in candidates]
    chosen = rng.choice(len(candidates), size=n, replace=False)
    return sorted(pd.Timestamp(candidates[i]) for i in chosen)


def stock_returns_from_prices(prices: pd.DataFrame) -> dict[str, pd.Series]:
    """Convert a long prices_daily DataFrame (cols ticker, trade_date,
    adj_close) into ``{ticker: returns Series}``."""
    out: dict[str, pd.Series] = {}
    for tk, grp in prices.groupby("ticker"):
        s = grp.set_index("trade_date").sort_index()["adj_close"]
        s.index = pd.to_datetime(s.index)
        out[str(tk)] = daily_returns(s)
    return out
