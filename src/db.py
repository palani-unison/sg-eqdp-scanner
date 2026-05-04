"""Pipeline data-store handles.

Originally backed by Supabase Postgres; the project has since pivoted to a
single DuckDB file at `data/eqdp.duckdb`. The pipeline call sites still
import `get_supabase()` and use the supabase-py builder pattern — that
keeps working because `src.store.DuckStore` exposes the same chain.

`get_pg_conn()` is retained for legacy bulk-DDL paths (e.g. `scripts/db_push`)
and now returns a raw DuckDB connection.
"""

from __future__ import annotations

from typing import Any

from .store import DuckStore, get_store


def get_supabase() -> DuckStore:
    """Backwards-compatible name. Returns a DuckDB-backed store."""
    return get_store()


def get_pg_conn(*, autocommit: bool = False) -> Any:
    """Raw DuckDB connection. `autocommit` is accepted for API parity but is
    a no-op — DuckDB autocommits each statement by default."""
    del autocommit
    return get_store().connect(read_only=False)
