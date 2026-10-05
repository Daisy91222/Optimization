from __future__ import annotations

import duckdb

from .config import DB_PATH, ensure_dirs


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    ensure_dirs()
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def execute_sql_file(con: duckdb.DuckDBPyConnection, path) -> None:
    con.execute(path.read_text(encoding="utf-8"))
