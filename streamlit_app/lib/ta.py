"""Technical-analysis helpers — pure pandas, no `pandas-ta` dependency.

Wrote these from first principles so the app does not depend on `pandas-ta`'s
numpy/pkg_resources shenanigans on Streamlit Cloud. Each function returns a
new Series aligned to the input.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(close: pd.Series, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def amihud(close: pd.Series, volume: pd.Series, window: int = 60) -> pd.Series:
    """Daily Amihud illiquidity = |return| / dollar_volume, rolling-mean smoothed."""
    ret = close.pct_change().abs()
    dollar_vol = (close * volume).replace(0.0, np.nan)
    daily = (ret / dollar_vol) * 1e9  # scale for readability
    return daily.rolling(window=window, min_periods=max(5, window // 4)).mean()


def returns(close: pd.Series, kind: str = "simple") -> pd.Series:
    if kind == "log":
        return np.log(close / close.shift(1))
    return close.pct_change()


def cumulative(simple_ret: pd.Series) -> pd.Series:
    return (1.0 + simple_ret.fillna(0.0)).cumprod() - 1.0
