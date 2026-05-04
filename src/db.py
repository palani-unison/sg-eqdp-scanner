"""Supabase + Postgres connections for the Python pipeline.

Two clients:
    - get_supabase(): high-level supabase-py REST client (service-role)
    - get_pg_conn():  raw psycopg2 connection via DB_DIRECT_CONNECTION

The pipeline writes use the service-role key (bypasses RLS). The web app
uses the anon key from web/.env.local — never imported here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

from supabase import Client, create_client

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _PROJECT_ROOT / ".env.local"


def _load_env() -> None:
    """Idempotent: load .env.local if present; never overrides existing env."""
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH, override=False)


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing required env var {name}. "
            f"Set it in {_ENV_PATH} or export it before running."
        )
    return val


def get_supabase() -> Client:
    """Service-role Supabase client. Bypasses RLS — pipeline writes only."""
    _load_env()
    url = _require("SUPABASE_URL")
    # Accept either name; SUPABASE_SERVICE_ROLE matches the user's .env.local,
    # SUPABASE_SERVICE_KEY matches the legacy .env.example placeholder.
    key = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_SERVICE_KEY")
    if not key:
        raise RuntimeError(
            "Missing SUPABASE_SERVICE_ROLE (or SUPABASE_SERVICE_KEY) in .env.local"
        )
    return create_client(url, key)


def get_pg_conn(*, autocommit: bool = False) -> Any:
    """Raw psycopg2 connection via DB_DIRECT_CONNECTION.

    Use for bulk schema work (db_push), DDL, or COPY-style ingest where the
    REST client is the wrong tool. Always close in a try/finally or `with`.
    """
    _load_env()
    dsn = _require("DB_DIRECT_CONNECTION")
    conn = psycopg2.connect(dsn)
    conn.autocommit = autocommit
    return conn
