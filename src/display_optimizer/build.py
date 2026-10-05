from __future__ import annotations

from .config import SQL_DIR
from .db import connect, execute_sql_file

BASE_SQL = [
    "00_raw.sql",
    "10_dimensions.sql",
    "20_facts.sql",
    "30_marts.sql",
    "40_quality.sql",
    "50_analysis.sql",
]


def build_base() -> None:
    con = connect()
    try:
        for name in BASE_SQL:
            execute_sql_file(con, SQL_DIR / name)
    finally:
        con.close()


def build_review() -> None:
    con = connect()
    try:
        execute_sql_file(con, SQL_DIR / "60_review.sql")
    finally:
        con.close()
