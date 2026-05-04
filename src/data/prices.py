"""yfinance adapter — fetch SGX OHLCV in long format matching prices_daily.

Contract:
    fetch_prices(symbols, start, end) -> pd.DataFrame with columns:
        ticker, trade_date, open, high, low, close, adj_close, volume,
        fetched_at_utc

Adjustments:
    Calls yfinance with ``auto_adjust=False`` so we keep BOTH raw close AND
    Adj Close — the schema has both columns. Returns/abnormal-returns are
    computed off ``adj_close`` (split-and-dividend-adjusted); raw close is
    preserved for audit and split-handling sanity checks.

Reliability:
    - 3 retries with exponential backoff (tenacity) on the network call.
    - Row-count, date-range, and null-rate assertions on every call.
    - Provenance: each row stamped with ``fetched_at_utc``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests
from tenacity import retry, stop_after_attempt, wait_exponential


@lru_cache(maxsize=1)
def _impersonating_session() -> Any:
    """Single curl_cffi Session impersonating Chrome.

    Yahoo Finance now blocks requests that lack a real browser TLS fingerprint.
    Without this, yfinance returns empty payloads with the
    ``YFTzMissingError('possibly delisted; no timezone found')`` symptom.
    """
    return curl_requests.Session(impersonate="chrome")

# Final wire columns in order — match prices_daily schema (plus fetched_at_utc).
WIRE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "fetched_at_utc",
)

# Yahoo's per-symbol field names (new yfinance versions).
_YF_FIELDS = ("Open", "High", "Low", "Close", "Adj Close", "Volume")


class PriceFetchError(RuntimeError):
    """Raised when the fetch returns data that fails validation."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _yf_download(
    symbols: list[str], start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    return yf.download(  # type: ignore[no-any-return]
        tickers=symbols,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=False,
        actions=False,
        group_by="ticker",
        threads=True,
        progress=False,
        session=_impersonating_session(),
    )


def _melt_to_long(raw: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    """Convert yfinance's wide DataFrame (single- or multi-symbol) to long."""
    frames: list[pd.DataFrame] = []

    if isinstance(raw.columns, pd.MultiIndex):
        # Multi-symbol: top level = ticker, second = field.
        present_symbols = sorted({s for s, _ in raw.columns})
        for sym in present_symbols:
            try:
                sub = raw[sym].copy()
            except KeyError:
                continue
            frames.append(_per_symbol_long(sub, sym))
    else:
        # Single symbol: flat columns Open, High, Low, Close, Adj Close, Volume.
        if len(symbols) != 1:
            # Some yf paths flatten when only one symbol returns data.
            (sym,) = (symbols[:1] or ["UNKNOWN"])
        else:
            sym = symbols[0]
        frames.append(_per_symbol_long(raw, sym))

    if not frames:
        return pd.DataFrame(columns=list(WIRE_COLUMNS))
    return pd.concat(frames, ignore_index=True)


def _per_symbol_long(sub: pd.DataFrame, symbol: str) -> pd.DataFrame:
    sub = sub.copy()
    sub.index = pd.to_datetime(sub.index)
    if sub.index.tz is not None:
        sub.index = sub.index.tz_localize(None)
    # Some symbols come back fully empty; drop those.
    sub = sub.dropna(how="all")
    if sub.empty:
        return pd.DataFrame(columns=list(WIRE_COLUMNS))

    out = pd.DataFrame(index=sub.index)
    out["ticker"] = symbol
    out["trade_date"] = pd.DatetimeIndex(sub.index).date
    out["open"] = sub.get("Open")
    out["high"] = sub.get("High")
    out["low"] = sub.get("Low")
    out["close"] = sub.get("Close")
    out["adj_close"] = sub.get("Adj Close")
    out["volume"] = sub.get("Volume")
    out = out.reset_index(drop=True)
    out["volume"] = out["volume"].fillna(0).astype("int64")
    return out[list(WIRE_COLUMNS[:-1])]  # all except fetched_at_utc


def _validate(
    df: pd.DataFrame,
    symbols: list[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    max_null_rate: float,
    min_rows_per_year_per_symbol: int,
) -> None:
    if df.empty:
        raise PriceFetchError(
            f"Empty result for {len(symbols)} symbols across {start.date()}..{end.date()}"
        )

    # Date range must be within [start, end] (inclusive of trading days only).
    min_date = pd.Timestamp(df["trade_date"].min())
    max_date = pd.Timestamp(df["trade_date"].max())
    if min_date < start - pd.Timedelta(days=1):
        raise PriceFetchError(
            f"trade_date {min_date.date()} earlier than requested start {start.date()}"
        )
    if max_date > end + pd.Timedelta(days=1):
        raise PriceFetchError(
            f"trade_date {max_date.date()} later than requested end {end.date()}"
        )

    # Null rate on the OHLC core (volume is allowed to be 0; adj_close may be
    # missing on splits-adjusted edge dates — we still flag if pervasive).
    core_cols = ["open", "high", "low", "close", "adj_close"]
    null_rate = df[core_cols].isna().mean().max()
    if null_rate > max_null_rate:
        raise PriceFetchError(
            f"null rate {null_rate:.3f} exceeds max {max_null_rate:.3f} on {core_cols}"
        )

    # Row-count sanity: roughly 252 trading days/year * #symbols, with slack.
    years = max((end - start).days / 365.25, 1.0 / 12.0)
    expected = int(min_rows_per_year_per_symbol * years * len(symbols) * 0.5)
    if len(df) < expected:
        raise PriceFetchError(
            f"row count {len(df)} < expected lower bound {expected} "
            f"(symbols={len(symbols)}, years={years:.2f})"
        )


def fetch_prices(
    symbols: list[str],
    start: pd.Timestamp | str,
    end: pd.Timestamp | str,
    *,
    max_null_rate: float = 0.05,
    min_rows_per_year_per_symbol: int = 200,
) -> pd.DataFrame:
    """Fetch OHLCV for symbols in [start, end]; return long DataFrame.

    All financial dates are tz-naive ``pd.Timestamp``. The returned DataFrame
    has columns matching ``WIRE_COLUMNS`` and is safe to upsert into the
    ``prices_daily`` table.
    """
    if not symbols:
        raise ValueError("symbols list is empty")

    start_ts = pd.Timestamp(start).tz_localize(None)
    end_ts = pd.Timestamp(end).tz_localize(None)
    if end_ts <= start_ts:
        raise ValueError(f"end ({end_ts}) must be after start ({start_ts})")

    raw = _yf_download(list(symbols), start_ts, end_ts)
    long_df = _melt_to_long(raw, list(symbols))

    _validate(
        long_df,
        symbols,
        start_ts,
        end_ts,
        max_null_rate=max_null_rate,
        min_rows_per_year_per_symbol=min_rows_per_year_per_symbol,
    )

    long_df["fetched_at_utc"] = datetime.now(UTC).isoformat()
    return long_df[list(WIRE_COLUMNS)]
