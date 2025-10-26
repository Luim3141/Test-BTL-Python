"""Utilities for interacting with the project SQLite database."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping, Sequence

DEFAULT_DB_PATH = Path("data/premier_league.db")


def ensure_database(path: Path = DEFAULT_DB_PATH) -> Path:
    """Ensure that the SQLite database file exists and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Touch the file to create an empty database.
        path.touch()
    return path


def connect(path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create a SQLite connection using the configured path."""
    db_path = Path(path)
    ensure_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_table(connection: sqlite3.Connection, name: str, columns: Mapping[str, str]) -> None:
    """Create (or replace) a table with the provided schema definition.

    Args:
        connection: Active SQLite connection.
        name: Name of the table to create.
        columns: Mapping of column names to SQLite column definitions.
    """
    cols_sql = ", ".join(f"{col} {definition}" for col, definition in columns.items())
    with connection:
        connection.execute(f"DROP TABLE IF EXISTS {name}")
        connection.execute(f"CREATE TABLE {name} ({cols_sql})")


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: Iterable[Mapping[str, object]],
    conflict_keys: Sequence[str] | None = None,
) -> None:
    """Insert or update rows in the specified table.

    Args:
        connection: Active SQLite connection.
        table: Table name where the rows will be inserted.
        rows: Iterable of dictionaries representing rows.
        conflict_keys: Optional list of columns used for upsert conflict resolution.
    """
    rows = list(rows)
    if not rows:
        return

    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    values = [[row.get(col) for col in columns] for row in rows]

    if conflict_keys:
        conflict_clause = ", ".join(conflict_keys)
        update_clause = ", ".join(f"{col}=excluded.{col}" for col in columns if col not in conflict_keys)
        sql = (
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_clause}) DO UPDATE SET {update_clause}"
        )
    else:
        sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"

    with connection:
        connection.executemany(sql, values)


def fetch_all(connection: sqlite3.Connection, query: str, params: Sequence[object] | None = None) -> list[sqlite3.Row]:
    """Fetch all rows for the provided query and return them as a list."""
    with connection:
        cursor = connection.execute(query, params or [])
        return cursor.fetchall()


__all__ = [
    "DEFAULT_DB_PATH",
    "ensure_database",
    "connect",
    "create_table",
    "upsert_rows",
    "fetch_all",
]
