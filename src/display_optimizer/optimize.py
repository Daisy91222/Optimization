from __future__ import annotations

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from .config import OUTPUTS, ensure_dirs
from .db import connect
from .simulate import generate_audits

MAX_CHANGES = 4
LOW_CONFIDENCE = 0.25
MAX_LOW_CONFIDENCE = 1


def _score(row: pd.Series) -> float:
    change_penalty = row["change_cost"] if row["is_change"] else 0.0
    return (
        row["predicted_incremental_sales"] * row["confidence"] * row["strategic_weight"]
        - 0.0001 * change_penalty
    )


def _solve_store(df: pd.DataFrame, relaxed: bool = False) -> tuple[pd.DataFrame, str]:
    model = cp_model.CpModel()
    variables = {idx: model.new_bool_var(f"x_{idx}") for idx in df.index}
    for _, slot in df.groupby("resource_position"):
        model.add(sum(variables[i] for i in slot.index) == 1)
    for idx, row in df.iterrows():
        if not bool(row["is_compatible"]):
            model.add(variables[idx] == 0)
    for category, group in df.groupby("category"):
        max_count = int(group["max_facings_per_store"].iloc[0])
        model.add(sum(variables[i] for i in group.index) <= max_count)
        if not relaxed and bool(group["is_headquarters_strategic"].iloc[0]):
            min_count = int(group["min_facings_per_store"].iloc[0])
            model.add(sum(variables[i] for i in group.index) >= min_count)
    if not relaxed:
        model.add(sum(variables[i] for i, r in df.iterrows() if r["is_change"]) <= MAX_CHANGES)
        model.add(
            sum(variables[i] for i, r in df.iterrows() if r["confidence"] < LOW_CONFIDENCE)
            <= MAX_LOW_CONFIDENCE
        )
    model.maximize(sum(round(_score(r) * 1000) * variables[i] for i, r in df.iterrows()))
    solver = cp_model.CpSolver()
    # Demo instances are deliberately bounded for one-command portfolio runs.
    solver.parameters.max_time_in_seconds = 2
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    status_name = solver.status_name(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return df.iloc[0:0].copy(), status_name
    chosen = df.loc[[i for i in df.index if solver.value(variables[i])]].copy()
    return chosen, ("RELAXED_" if relaxed else "") + status_name


def _greedy(df: pd.DataFrame) -> pd.DataFrame:
    eligible = df[df["is_compatible"]].copy()
    # Deliberately unconstrained benchmark: rank by model-estimated efficiency only.
    eligible["objective_score"] = eligible["predicted_incremental_sales"] * eligible["confidence"]
    return eligible.sort_values(
        ["resource_position", "objective_score"], ascending=[True, False]
    ).drop_duplicates("resource_position")


def _current(df: pd.DataFrame) -> pd.DataFrame:
    current = df[df["category"] == df["current_category"]].drop_duplicates("resource_position")
    return current


def _safe_fallback(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per slot even when a slot has no compatible candidate."""
    chosen = _greedy(df)
    missing = set(df["resource_position"]) - set(chosen["resource_position"])
    if missing:
        current = _current(df[df["resource_position"].isin(missing)])
        chosen = pd.concat([chosen, current], ignore_index=False)
        missing -= set(current["resource_position"])
    if missing:
        emergency = (
            df[df["resource_position"].isin(missing)]
            .sort_values(["resource_position", "confidence"], ascending=[True, False])
            .drop_duplicates("resource_position")
        )
        chosen = pd.concat([chosen, emergency], ignore_index=False)
    return chosen.drop_duplicates("resource_position")


def _violations(selected: pd.DataFrame) -> int:
    violations = int((~selected["is_compatible"]).sum())
    if selected["is_change"].sum() > MAX_CHANGES:
        violations += 1
    if (selected["confidence"] < LOW_CONFIDENCE).sum() > MAX_LOW_CONFIDENCE:
        violations += 1
    for _, group in selected.groupby("category"):
        if len(group) > int(group["max_facings_per_store"].iloc[0]):
            violations += 1
    strategic = selected[selected["is_headquarters_strategic"]]
    if strategic.empty:
        violations += 1
    return violations


def _metrics(name: str, selected: pd.DataFrame, category_total: int) -> dict:
    change = selected[selected["is_change"]]
    return {
        "scenario": name,
        "predicted_incremental_sales": round(
            float(selected["predicted_incremental_sales"].sum()), 2
        ),
        "change_count": len(change),
        "change_cost": round(float(change["change_cost"].sum()), 2),
        "category_coverage_rate": round(float(selected["category"].nunique() / category_total), 4),
        "brand_concentration": round(
            float(selected["dominant_brand"].value_counts(normalize=True).max()), 4
        ),
        "low_confidence_share": round(float((selected["confidence"] < LOW_CONFIDENCE).mean()), 4),
        "constraint_violations": _violations(selected),
        "data_source": "scenario_simulation_from_model_estimates",
    }


def optimize_allocations() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_dirs()
    con = connect()
    candidates = con.execute("select * from mart_allocation_candidates").df()
    solutions = []
    diagnostics = []
    scenario_rows = []
    category_total = candidates["category"].nunique()
    for store, store_df in candidates.groupby("store_id"):
        store_df = store_df.copy()
        chosen, status = _solve_store(store_df)
        if chosen.empty:
            diagnostics.append(
                {
                    "store_id": store,
                    "initial_status": status,
                    "diagnosis": "hard policy set infeasible; relaxed change/confidence/strategic constraints",
                    "fallback": "relaxed_cp_sat",
                }
            )
            chosen, status = _solve_store(store_df, relaxed=True)
        if chosen.empty:
            diagnostics[-1]["fallback"] = "greedy_eligible"
            chosen = _safe_fallback(store_df)
            status = "GREEDY_EMERGENCY_FALLBACK"
        chosen["solver_status"] = status
        solutions.append(chosen)
        for scenario, frame in {
            "current_configuration": _current(store_df),
            "historical_efficiency_greedy": _greedy(store_df),
            "ortools_constrained": chosen,
        }.items():
            row = _metrics(scenario, frame, category_total)
            row["store_id"] = store
            scenario_rows.append(row)

    selected = pd.concat(solutions, ignore_index=True)
    selected["recommendation_id"] = [f"REC-{i + 1:06d}" for i in range(len(selected))]
    selected["recommended_category"] = selected["category"]
    selected["reason_code"] = np.select(
        [
            ~selected["is_change"],
            selected["is_headquarters_strategic"],
            selected["confidence"] >= 0.7,
        ],
        ["RETAIN_COST_CONTROL", "HQ_STRATEGIC", "HIGH_CONFIDENCE_LIFT"],
        default="CONSTRAINT_BALANCE",
    )
    recommendations = selected[
        [
            "recommendation_id",
            "store_id",
            "target_week",
            "resource_position",
            "resource_type",
            "recommended_category",
            "current_category",
            "predicted_incremental_sales",
            "confidence",
            "change_cost",
            "reason_code",
            "solver_status",
            "model_version",
            "data_source",
        ]
    ].copy()
    scenarios = pd.DataFrame(scenario_rows)
    diagnostics_df = pd.DataFrame(
        diagnostics, columns=["store_id", "initial_status", "diagnosis", "fallback"]
    )
    recommendations.to_csv(OUTPUTS / "allocation_recommendations.csv", index=False)
    scenarios.to_csv(OUTPUTS / "scenario_comparison.csv", index=False)
    diagnostics_df.to_csv(OUTPUTS / "infeasibility_diagnostics.csv", index=False)

    con.register("recommendation_df", recommendations)
    con.register("scenario_df", scenarios)
    con.register("diagnostic_df", diagnostics_df)
    con.execute(
        "create or replace table mart_allocation_recommendations as select * from recommendation_df"
    )
    con.execute("create or replace table mart_scenario_comparison as select * from scenario_df")
    con.execute(
        "create or replace table mart_infeasibility_diagnostics as select * from diagnostic_df"
    )
    audits = generate_audits(recommendations)
    con.register("audit_df", audits)
    con.execute("create or replace table mart_space_audit as select * from audit_df")
    con.close()
    return recommendations, scenarios
