"""Initialise data/eqdp.duckdb from db/schema_duckdb.sql.

Idempotent — every CREATE in the schema uses IF NOT EXISTS, so re-running
this against an existing file is safe.

Usage:
    python -m scripts.init_duckdb            # create at the canonical path
    EQDP_DB_PATH=/tmp/x.duckdb python -m scripts.init_duckdb
"""

from __future__ import annotations

from pathlib import Path

from src.store import db_path, get_store


def main() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "db" / "schema_duckdb.sql"
    if not schema_path.exists():
        raise SystemExit(f"missing schema file: {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")
    store = get_store()
    target = db_path()
    print(f"applying {schema_path.name} → {target}")
    with store.connect() as conn:
        # DuckDB happily parses multi-statement SQL via .execute().
        conn.execute(sql)
    print(f"ok — schema applied at {target} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
