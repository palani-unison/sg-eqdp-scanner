"""Cached DuckDB reader for the Streamlit app.

The app reads from a single file at `data/eqdp.duckdb` (overridable via the
`EQDP_DB_PATH` env var). DuckDB opens the file in read-only mode so multiple
Streamlit sessions can read concurrently without lock contention.

Public function names match the original `lib.supabase` module so page
imports do not need to change.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import duckdb
import pandas as pd
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _PROJECT_ROOT / "data" / "eqdp.duckdb"


def _db_path() -> Path:
    override = os.getenv("EQDP_DB_PATH")
    return Path(override) if override else _DEFAULT_DB


@contextmanager
def _connect() -> Iterator[duckdb.DuckDBPyConnection]:
    path = _db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB file not found at {path}. "
            f"Run `python -m scripts.init_duckdb` to create it, then run the pipelines."
        )
    conn = duckdb.connect(str(path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def _query(sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    with _connect() as conn:
        return conn.execute(sql, params or []).df()


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def load_tickers() -> pd.DataFrame:
    df = _query(
        """
        SELECT ticker, sgx_code, name, sector, market_cap_band, listing_board,
               in_sti30, in_next50, restricted_sector,
               t1_flag, t2_flag, t3_flag, broker_named_count
        FROM tickers
        ORDER BY ticker
        """
    )
    if df.empty:
        return df
    df["headline_tier"] = df.apply(_headline_tier, axis=1)
    return df


def _headline_tier(row: pd.Series) -> str:
    if row.get("t1_flag"):
        return "T1"
    if row.get("t2_flag"):
        return "T2"
    if row.get("t3_flag"):
        return "T3"
    if row.get("in_sti30"):
        return "control"
    return "none"


@st.cache_data(ttl=900, show_spinner=False)
def load_latest_scores(top_n: int = 50) -> pd.DataFrame:
    latest = _query("SELECT MAX(score_date) AS d FROM candidate_scores")
    if latest.empty or pd.isna(latest.iloc[0]["d"]):
        return pd.DataFrame()
    d = latest.iloc[0]["d"]
    sql = """
        SELECT c.ticker,
               t.name,
               COALESCE(t.sgx_code, REPLACE(c.ticker, '.SI', '')) AS sgx_code,
               c.score_date, c.liquidity_rise, c.institutional_proxy,
               c.index_inclusion, c.broker_named, c.filing_present,
               c.total_score, c.eqdp_tier
        FROM candidate_scores c
        LEFT JOIN tickers t USING (ticker)
        WHERE c.score_date = ?
        ORDER BY c.total_score DESC
    """
    df = _query(sql, [d])
    if df.empty:
        return df
    df["score_date"] = pd.to_datetime(df["score_date"]).dt.date
    df["sgx_url"] = "https://investors.sgx.com/market/security-details/stocks/" + df[
        "sgx_code"
    ].fillna("")
    return df.head(top_n) if top_n else df


@st.cache_data(ttl=900, show_spinner=False)
def load_prices(ticker: str, start: str | None = None) -> pd.DataFrame:
    if start:
        df = _query(
            """
            SELECT trade_date, open, high, low, close, adj_close, volume
            FROM prices_daily
            WHERE ticker = ? AND trade_date >= CAST(? AS DATE)
            ORDER BY trade_date
            """,
            [ticker, start],
        )
    else:
        df = _query(
            """
            SELECT trade_date, open, high, low, close, adj_close, volume
            FROM prices_daily
            WHERE ticker = ?
            ORDER BY trade_date
            """,
            [ticker],
        )
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for col in ("open", "high", "low", "close", "adj_close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int64")
    return df.reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_event_study(event_id: str, benchmark: str = "capm") -> pd.DataFrame:
    df = _query(
        """
        SELECT ticker, t, ar, car
        FROM abnormal_returns
        WHERE event_id = ? AND benchmark = ?
        ORDER BY t
        """,
        [event_id, benchmark],
    )
    if df.empty:
        return df
    df["ar"] = pd.to_numeric(df["ar"], errors="coerce")
    df["car"] = pd.to_numeric(df["car"], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_did_forest() -> pd.DataFrame:
    df = _query(
        """
        SELECT metric, scope, point_estimate, lower_5, upper_95
        FROM bootstrap_cis
        WHERE metric = 'did_delta'
        """
    )
    if df.empty:
        return df
    for col in ("point_estimate", "lower_5", "upper_95"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=900, show_spinner=False)
def load_filings(limit: int | None = 200) -> pd.DataFrame:
    sql = """
        SELECT filing_id, manager_id, ticker, effective_date, filing_date,
               stake_pct, direction, source_url
        FROM filings_t1
        ORDER BY filing_date DESC
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    df = _query(sql)
    if df.empty:
        return df
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.date
    df["effective_date"] = pd.to_datetime(df["effective_date"]).dt.date
    df["stake_pct"] = pd.to_numeric(df["stake_pct"], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_managers() -> pd.DataFrame:
    return _query(
        "SELECT manager_id, canonical_name, aliases, tranche, appointed_date "
        "FROM eqdp_managers ORDER BY tranche, canonical_name"
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_factor_returns(start: str = "2024-01-02") -> pd.DataFrame:
    df = _query(
        """
        SELECT trade_date, market, smb, hml
        FROM factor_returns
        WHERE trade_date >= CAST(? AS DATE)
        ORDER BY trade_date
        """,
        [start],
    )
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for col in ("market", "smb", "hml"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def latest_pipeline_runs(limit: int = 10) -> pd.DataFrame:
    df = _query(
        """
        SELECT job_name, started_at, completed_at, status
        FROM pipeline_runs
        ORDER BY started_at DESC
        LIMIT ?
        """,
        [int(limit)],
    )
    if df.empty:
        return df
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["completed_at"] = pd.to_datetime(df["completed_at"])
    return df


def db_exists() -> bool:
    """True if the DuckDB file is present — used to render a friendly empty state."""
    return _db_path().exists()
