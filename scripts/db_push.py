"""Apply db/schema.sql and any db/migrations/*.sql to the Supabase Postgres
project named in .env.local. Idempotent (schema.sql uses ``if not exists``).

Usage:
    python -m scripts.db_push                # apply schema + migrations
    python -m scripts.db_push --dry-run      # show what would run
    python -m scripts.db_push --schema-only  # skip migrations dir

Edge functions live under ``db/edge_functions/`` and are Deno/TypeScript —
deploy those with ``supabase functions deploy <name>`` (the Supabase CLI),
NOT this script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from src.db import get_pg_conn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
MIGRATIONS_DIR = PROJECT_ROOT / "db" / "migrations"
EDGE_FN_DIR = PROJECT_ROOT / "db" / "edge_functions"

console = Console()
app = typer.Typer(add_completion=False, help=__doc__)


def _collect_sql_files(schema_only: bool) -> list[Path]:
    files: list[Path] = []
    if SCHEMA_PATH.exists():
        files.append(SCHEMA_PATH)
    else:
        raise FileNotFoundError(f"Missing {SCHEMA_PATH}")
    if not schema_only and MIGRATIONS_DIR.exists():
        files.extend(sorted(MIGRATIONS_DIR.glob("*.sql")))
    return files


def _run_sql_file(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    if not sql.strip():
        console.print(f"  [dim]skipped (empty): {path.name}[/]")
        return
    # autocommit so CREATE EXTENSION + DDL each commit independently;
    # schema.sql is idempotent so partial-apply on error is recoverable.
    conn = get_pg_conn(autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        console.print(f"  [green]applied[/]: {path.relative_to(PROJECT_ROOT)}")
    finally:
        conn.close()


@app.command()
def main(
    dry_run: bool = typer.Option(False, "--dry-run", help="List files, do not execute."),
    schema_only: bool = typer.Option(False, "--schema-only", help="Skip db/migrations/."),
) -> None:
    files = _collect_sql_files(schema_only=schema_only)
    console.print(f"[bold]db_push[/] — {len(files)} file(s) to apply:")
    for f in files:
        console.print(f"  • {f.relative_to(PROJECT_ROOT)}")

    if dry_run:
        console.print("[yellow]dry-run: nothing executed.[/]")
        _print_edge_fn_hint()
        return

    for f in files:
        try:
            _run_sql_file(f)
        except Exception as exc:
            console.print(f"[red]FAILED on {f.name}:[/] {exc}")
            sys.exit(1)

    console.print("[bold green]db_push complete.[/]")
    _print_edge_fn_hint()


def _print_edge_fn_hint() -> None:
    if EDGE_FN_DIR.exists() and any(EDGE_FN_DIR.iterdir()):
        console.print(
            "\n[dim]Edge functions detected under db/edge_functions/. "
            "Deploy them with the Supabase CLI:\n"
            "  supabase functions deploy <name>[/]"
        )


if __name__ == "__main__":
    app()
