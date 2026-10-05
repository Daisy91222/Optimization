from __future__ import annotations

import argparse

from .build import build_base, build_review
from .config import DB_PATH, DEMO, OUTPUTS, ensure_dirs
from .model import fit_baseline_and_candidates
from .optimize import optimize_allocations
from .simulate import generate_simulated_inputs


def run_all() -> None:
    ensure_dirs()
    required = [DEMO / f"{name}.parquet" for name in ("transactions", "promotions", "products")]
    if not all(path.exists() for path in required):
        raise FileNotFoundError("Demo files missing. Run `make demo` first.")
    print("[1/5] Building raw, dimensional, fact, mart, and quality SQL layers")
    build_base()
    print("[2/5] Generating source-labelled simulated business configuration")
    generate_simulated_inputs()
    print("[3/5] Fitting interpretable baseline and candidate estimates")
    metrics = fit_baseline_and_candidates()
    print(f"      temporal test MAE={metrics['mae']}, R2={metrics['r2']}")
    print("[4/5] Solving constrained allocations and baseline scenarios")
    recommendations, scenarios = optimize_allocations()
    print(f"      {len(recommendations)} recommendations; {len(scenarios)} scenario rows")
    print("[5/5] Building recommendation-to-audit review views")
    build_review()
    print(f"Complete: {DB_PATH}")


def clean() -> None:
    for path in [
        DB_PATH,
        OUTPUTS / "allocation_recommendations.csv",
        OUTPUTS / "scenario_comparison.csv",
    ]:
        if path.exists():
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(prog="display-opt")
    parser.add_argument("command", choices=["run-all", "build-sql", "optimize", "clean"])
    args = parser.parse_args()
    if args.command == "run-all":
        run_all()
    elif args.command == "build-sql":
        build_base()
    elif args.command == "optimize":
        optimize_allocations()
        build_review()
    else:
        clean()


if __name__ == "__main__":
    main()
