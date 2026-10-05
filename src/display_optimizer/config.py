from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DEMO = DATA / "demo"
SIMULATED = DATA / "simulated"
WAREHOUSE = DATA / "warehouse"
OUTPUTS = ROOT / "outputs"
SQL_DIR = ROOT / "sql"
DB_PATH = WAREHOUSE / "display_optimization.duckdb"


def ensure_dirs() -> None:
    for path in (DEMO, SIMULATED, WAREHOUSE, OUTPUTS, OUTPUTS / "figures"):
        path.mkdir(parents=True, exist_ok=True)
