"""Cached Supabase read client for the Streamlit app.

Uses the anon key — RLS policies in db/schema.sql grant public SELECT on every
analytical table, so the app can render entirely from anon-key reads. The
service-role key is loaded only if explicitly present (e.g. for the optional
registration form on Streamlit Cloud).

The PostgREST endpoint silently caps responses at 1000 rows; `select_all()`
pages with `.range()` so callers never have to think about it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client


def _secret(name: str, default: str | None = None) -> str | None:
    """Read from st.secrets first (Streamlit Cloud), then env (local dev)."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):  # type: ignore[attr-defined]
        pass
    except Exception:
        pass
    return os.getenv(name, default)


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in "
            ".streamlit/secrets.toml (or env vars). See secrets.toml.example."
        )
    return create_client(url, key)


@st.cache_resource(show_spinner=False)
def get_service_client() -> Client | None:
    """Service-role client for the optional registration form. None if absent."""
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_SERVICE_ROLE")
    if not url or not key:
        return None
    return create_client(url, key)


def select_all(
    table: str,
    columns: str = "*",
    *,
    filters: list[tuple[str, str, Any]] | None = None,
    order: tuple[str, bool] | None = None,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    """Page through PostgREST until exhausted, defeating the 1000-row cap.

    `filters` items are (column, op, value) tuples. Supported ops: eq, gte,
    lte, gt, lt, in_. `order` is (column, ascending).
    """
    client = get_client()
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        q = client.table(table).select(columns)
        for col, op, val in filters or []:
            q = getattr(q, op)(col, val)
        if order is not None:
            q = q.order(order[0], desc=not order[1])
        q = q.range(offset, offset + page_size - 1)
        resp = q.execute()
        chunk = resp.data or []
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return rows


@st.cache_data(ttl=3600, show_spinner=False)
def load_tickers() -> pd.DataFrame:
    rows = select_all(
        "tickers",
        columns=(
            "ticker, sgx_code, name, sector, market_cap_band, listing_board, "
            "in_sti30, in_next50, restricted_sector, "
            "t1_flag, t2_flag, t3_flag, broker_named_count"
        ),
    )
    df = pd.DataFrame(rows)
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
    """Most recent candidate-score snapshot — one row per ticker."""
    client = get_client()
    resp = (
        client.table("candidate_scores")
        .select("score_date")
        .order("score_date", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return pd.DataFrame()
    latest = resp.data[0]["score_date"]
    rows = select_all(
        "candidate_scores",
        filters=[("score_date", "eq", latest)],
        order=("total_score", False),
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["score_date"] = pd.to_datetime(df["score_date"]).dt.date
    return df.head(top_n) if top_n else df


@st.cache_data(ttl=900, show_spinner=False)
def load_prices(ticker: str, start: str | None = None) -> pd.DataFrame:
    filters: list[tuple[str, str, Any]] = [("ticker", "eq", ticker)]
    if start:
        filters.append(("trade_date", "gte", start))
    rows = select_all(
        "prices_daily",
        columns="trade_date, open, high, low, close, adj_close, volume",
        filters=filters,
        order=("trade_date", True),
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for col in ("open", "high", "low", "close", "adj_close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int64")
    return df.sort_values("trade_date").reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_event_study(event_id: str, benchmark: str = "capm") -> pd.DataFrame:
    rows = select_all(
        "abnormal_returns",
        columns="ticker, t, ar, car",
        filters=[("event_id", "eq", event_id), ("benchmark", "eq", benchmark)],
        order=("t", True),
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ar"] = pd.to_numeric(df["ar"], errors="coerce")
    df["car"] = pd.to_numeric(df["car"], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_did_forest() -> pd.DataFrame:
    rows = select_all(
        "bootstrap_cis",
        filters=[("metric", "eq", "did_delta")],
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("point_estimate", "lower_5", "upper_95"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=900, show_spinner=False)
def load_filings(limit: int | None = 200) -> pd.DataFrame:
    rows = select_all(
        "filings_t1",
        columns=(
            "filing_id, manager_id, ticker, effective_date, filing_date, "
            "stake_pct, direction, source_url"
        ),
        order=("filing_date", False),
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.date
    df["effective_date"] = pd.to_datetime(df["effective_date"]).dt.date
    df["stake_pct"] = pd.to_numeric(df["stake_pct"], errors="coerce")
    return df.head(limit) if limit else df


@st.cache_data(ttl=3600, show_spinner=False)
def load_managers() -> pd.DataFrame:
    rows = select_all("eqdp_managers", order=("tranche", True))
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def load_factor_returns(start: str = "2024-01-02") -> pd.DataFrame:
    rows = select_all(
        "factor_returns",
        columns="trade_date, market, smb, hml",
        filters=[("trade_date", "gte", start)],
        order=("trade_date", True),
    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for col in ("market", "smb", "hml"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def latest_pipeline_runs(limit: int = 10) -> pd.DataFrame:
    client = get_client()
    resp = (
        client.table("pipeline_runs")
        .select("job_name, started_at, completed_at, status")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    df = pd.DataFrame(resp.data or [])
    if df.empty:
        return df
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["completed_at"] = pd.to_datetime(df["completed_at"])
    return df
