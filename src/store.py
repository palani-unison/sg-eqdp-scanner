"""DuckDB-backed store with a supabase-py-compatible chainable API.

The pipelines were written against `supabase-py`. This module exposes the
same call shapes — `.table(name).upsert(rows, on_conflict=...).execute()`,
`.table(name).select("*").eq("ticker", "X").order("d", desc=True).execute()`,
etc. — but reads/writes a local DuckDB file at `data/eqdp.duckdb`.

Why a shim instead of rewriting the pipelines? Two reasons:
1. Smallest diff. Pipelines call `client.table(...)` in ~20 places; one shim
   means we don't touch any of them.
2. The supabase-py builder pattern is reasonable; replicating it lets the
   abstraction stay where it belongs (in store.py) rather than leaking
   DuckDB-specific SQL into every pipeline.

The streamlit app uses the lower-level `read_sql()` / `read_table()` helpers
in `streamlit_app/lib/store.py` because it doesn't need the chain.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import duckdb
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = _PROJECT_ROOT / "data" / "eqdp.duckdb"
_LOCK = threading.RLock()


def db_path() -> Path:
    """Resolve the DuckDB file location. Override with $EQDP_DB_PATH for tests."""
    override = os.getenv("EQDP_DB_PATH")
    return Path(override) if override else _DEFAULT_DB


def get_connection(*, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, ensuring the parent directory exists."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


@dataclass
class _Result:
    """Mimics the supabase-py response object — `resp.data` is what callers read."""

    data: list[dict[str, Any]] = field(default_factory=list)
    count: int | None = None


@dataclass
class _Filter:
    op: str
    col: str
    val: Any


class _Query:
    """Chainable query builder — builds up a SELECT or an UPDATE."""

    def __init__(
        self,
        store: "DuckStore",
        table: str,
        *,
        mode: str,
        select_cols: str | None = None,
        update_values: dict[str, Any] | None = None,
        with_count: bool = False,
    ) -> None:
        self._store = store
        self._table = table
        self._mode = mode  # "select" or "update"
        self._select = select_cols or "*"
        self._update_values = update_values or {}
        self._filters: list[_Filter] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None
        self._with_count = with_count

    # ---- filters --------------------------------------------------------
    def eq(self, col: str, val: Any) -> "_Query":
        self._filters.append(_Filter("=", col, val))
        return self

    def gt(self, col: str, val: Any) -> "_Query":
        self._filters.append(_Filter(">", col, val))
        return self

    def gte(self, col: str, val: Any) -> "_Query":
        self._filters.append(_Filter(">=", col, val))
        return self

    def lt(self, col: str, val: Any) -> "_Query":
        self._filters.append(_Filter("<", col, val))
        return self

    def lte(self, col: str, val: Any) -> "_Query":
        self._filters.append(_Filter("<=", col, val))
        return self

    def in_(self, col: str, vals: Iterable[Any]) -> "_Query":
        self._filters.append(_Filter("IN", col, list(vals)))
        return self

    # ---- ordering / paging ---------------------------------------------
    def order(self, col: str, *, desc: bool = False) -> "_Query":
        self._order = (col, desc)
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "_Query":
        # Supabase .range() is inclusive on both ends; offset = start, limit = end - start + 1.
        self._range = (start, end)
        return self

    # ---- execute --------------------------------------------------------
    def execute(self) -> _Result:
        if self._mode == "select":
            return self._exec_select()
        if self._mode == "update":
            return self._exec_update()
        raise RuntimeError(f"unknown query mode: {self._mode}")

    # ---- internals ------------------------------------------------------
    def _where_sql(self) -> tuple[str, list[Any]]:
        if not self._filters:
            return "", []
        clauses: list[str] = []
        params: list[Any] = []
        for f in self._filters:
            if f.op == "IN":
                placeholders = ", ".join("?" for _ in f.val)
                clauses.append(f'"{f.col}" IN ({placeholders})')
                params.extend(f.val)
            else:
                clauses.append(f'"{f.col}" {f.op} ?')
                params.append(f.val)
        return " WHERE " + " AND ".join(clauses), params

    def _exec_select(self) -> _Result:
        sql = f'SELECT {self._select} FROM "{self._table}"'
        where, params = self._where_sql()
        sql += where
        if self._order is not None:
            col, desc = self._order
            sql += f' ORDER BY "{col}" {"DESC" if desc else "ASC"}'
        if self._range is not None:
            start, end = self._range
            sql += f" LIMIT {end - start + 1} OFFSET {start}"
        elif self._limit is not None:
            sql += f" LIMIT {self._limit}"
        with _LOCK, self._store._connect() as conn:
            df = conn.execute(sql, params).df()
            count: int | None = None
            if self._with_count:
                count_sql = f'SELECT count(*) AS n FROM "{self._table}"' + where
                count = int(conn.execute(count_sql, params).fetchone()[0])
        return _Result(data=df.to_dict(orient="records"), count=count)

    def _exec_update(self) -> _Result:
        if not self._update_values:
            return _Result(data=[])
        cols = list(self._update_values.keys())
        set_sql = ", ".join(f'"{c}" = ?' for c in cols)
        params: list[Any] = [self._update_values[c] for c in cols]
        sql = f'UPDATE "{self._table}" SET {set_sql}'
        where, where_params = self._where_sql()
        sql += where
        params.extend(where_params)
        with _LOCK, self._store._connect() as conn:
            conn.execute(sql, params)
        return _Result(data=[])


class _Insert:
    """Insert / upsert handle — terminal, no further chaining."""

    def __init__(
        self,
        store: "DuckStore",
        table: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str | None,
    ) -> None:
        self._store = store
        self._table = table
        self._rows = rows
        self._on_conflict = on_conflict

    def execute(self) -> _Result:
        rows = list(self._rows or [])
        if not rows:
            return _Result(data=[])
        cols = sorted({k for row in rows for k in row.keys()})
        col_sql = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join("?" for _ in cols)
        sql = f'INSERT INTO "{self._table}" ({col_sql}) VALUES ({placeholders})'
        if self._on_conflict:
            keys = [k.strip() for k in self._on_conflict.split(",")]
            updates = ", ".join(
                f'"{c}" = excluded."{c}"' for c in cols if c not in keys
            )
            conflict_cols = ", ".join(f'"{k}"' for k in keys)
            if updates:
                sql += f" ON CONFLICT ({conflict_cols}) DO UPDATE SET {updates}"
            else:
                sql += f" ON CONFLICT ({conflict_cols}) DO NOTHING"
        sql += " RETURNING *"
        with _LOCK, self._store._connect() as conn:
            # DuckDB's executemany doesn't materialise RETURNING rows the way
            # we need; loop and collect explicitly.
            returned: list[dict[str, Any]] = []
            for row in rows:
                params = [row.get(c) for c in cols]
                df = conn.execute(sql, params).df()
                returned.extend(df.to_dict(orient="records"))
        return _Result(data=returned)


class _Table:
    def __init__(self, store: "DuckStore", name: str) -> None:
        self._store = store
        self._name = name

    def select(self, cols: str = "*", *_args: Any, count: str | None = None, **_kwargs: Any) -> _Query:
        return _Query(
            self._store,
            self._name,
            mode="select",
            select_cols=cols,
            with_count=(count == "exact"),
        )

    def insert(self, rows: dict[str, Any] | list[dict[str, Any]]) -> _Insert:
        if isinstance(rows, dict):
            rows = [rows]
        return _Insert(self._store, self._name, rows, on_conflict=None)

    def upsert(
        self,
        rows: dict[str, Any] | list[dict[str, Any]],
        *,
        on_conflict: str | None = None,
        **_: Any,
    ) -> _Insert:
        if isinstance(rows, dict):
            rows = [rows]
        return _Insert(self._store, self._name, rows, on_conflict=on_conflict)

    def update(self, values: dict[str, Any]) -> _Query:
        return _Query(self._store, self._name, mode="update", update_values=values)


class DuckStore:
    """Thin facade. `store.table("X").upsert(...)` mirrors supabase-py."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self._path), read_only=False)

    def table(self, name: str) -> _Table:
        return _Table(self, name)

    # Convenience for code that wants a raw connection (DDL, COPY, etc.)
    def connect(self, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self._path), read_only=read_only)

    def read_df(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        with _LOCK, self._connect() as conn:
            return conn.execute(sql, params or []).df()


def get_store() -> DuckStore:
    """Lazily create a DuckStore against the canonical path."""
    return DuckStore()
