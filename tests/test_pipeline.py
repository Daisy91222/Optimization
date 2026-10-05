import duckdb

from display_optimizer.config import DB_PATH, ROOT
from display_optimizer.optimize import _safe_fallback


def test_required_artifacts_exist():
    required = [
        ROOT / "README.md",
        ROOT / "docs" / "data_dictionary.md",
        ROOT / "outputs" / "portfolio_report.html",
        ROOT / "outputs" / "allocation_recommendations.csv",
        DB_PATH,
    ]
    assert all(path.exists() for path in required)


def test_source_labels_and_quality():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    assert (
        con.execute(
            "select count(*) from raw_transactions where data_source <> 'real_anonymized'"
        ).fetchone()[0]
        == 0
    )
    assert (
        con.execute(
            "select count(*) from mart_space_audit where data_source <> 'simulated'"
        ).fetchone()[0]
        == 0
    )
    assert (
        con.execute(
            "select count(*) from mart_incremental_effect where data_source <> 'model_estimate'"
        ).fetchone()[0]
        == 0
    )
    assert con.execute("select count(*) from dq_results where status='FAIL'").fetchone()[0] == 0
    con.close()


def test_recommendation_grain_and_constraints():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    total, distinct_total = con.execute(
        "select count(*),count(distinct store_id||'|'||target_week||'|'||resource_position) from mart_allocation_recommendations"
    ).fetchone()
    assert total == distinct_total
    assert (
        con.execute(
            "select count(*) from mart_allocation_recommendations where solver_status not like '%OPTIMAL%' and solver_status not like '%FEASIBLE%'"
        ).fetchone()[0]
        == 0
    )
    assert (
        con.execute(
            "select sum(constraint_violations) from mart_scenario_comparison where scenario='ortools_constrained'"
        ).fetchone()[0]
        == 0
    )
    con.close()


def test_required_tables_are_nonempty():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables = [
        "raw_transactions",
        "raw_promotions",
        "raw_products",
        "dim_store",
        "dim_product",
        "dim_display_location",
        "dim_week",
        "fact_transactions",
        "fact_product_display",
        "fact_store_week_category",
        "mart_display_performance",
        "mart_display_baseline",
        "mart_incremental_effect",
        "mart_allocation_candidates",
        "mart_allocation_recommendations",
        "mart_space_audit",
    ]
    for table in tables:
        assert con.execute(f"select count(*) from {table}").fetchone()[0] > 0, table
    con.close()


def test_infeasible_fallback_keeps_one_assignment_per_slot():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    candidates = con.execute(
        "select * from mart_allocation_candidates where store_id=(select min(store_id) from mart_allocation_candidates)"
    ).df()
    con.close()
    one_slot = candidates["resource_position"] == candidates["resource_position"].iloc[0]
    candidates.loc[one_slot, "is_compatible"] = False
    fallback = _safe_fallback(candidates)
    assert fallback["resource_position"].nunique() == candidates["resource_position"].nunique()
    assert len(fallback) == candidates["resource_position"].nunique()
