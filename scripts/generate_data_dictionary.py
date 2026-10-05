#!/usr/bin/env python3
from __future__ import annotations

from display_optimizer.config import ROOT
from display_optimizer.db import connect

TABLE_META = {
    "raw_transactions": (
        "source_record_id",
        "receipt line",
        "real_anonymized",
        "unique record id; required keys; week range",
    ),
    "raw_promotions": (
        "none (source may duplicate product/store/week)",
        "source promotion row",
        "real_anonymized",
        "valid display/mailer codes; duplicate grain audited",
    ),
    "raw_products": (
        "product_id",
        "product",
        "real_anonymized",
        "product id required; duplicate id checked in dimension",
    ),
    "dim_store": ("store_id", "store", "real_anonymized", "unique, non-null store id"),
    "dim_product": (
        "product_id",
        "product",
        "real_anonymized",
        "unique product id; taxonomy null rate monitored",
    ),
    "dim_display_location": (
        "display_location",
        "display code",
        "official code mapping",
        "code uniqueness and allowed set",
    ),
    "dim_week": ("week", "retail week", "derived", "week 1-53"),
    "fact_transactions": (
        "source_record_id",
        "receipt line enriched with product",
        "real_anonymized",
        "product referential integrity",
    ),
    "fact_product_display": (
        "product_id, store_id, week",
        "product-store-week",
        "real_anonymized + deterministic duplicate resolution",
        "one row per grain; raw_record_count retained",
    ),
    "fact_store_week_category": (
        "store_id, week, product_category",
        "store-week-category",
        "aggregated real_anonymized",
        "additive measures; category required",
    ),
    "mart_display_performance": (
        "store_id, week, category, display_location, mailer_location",
        "store-week-category-display-mailer",
        "descriptive aggregation",
        "ranks partition correctly; no causal label",
    ),
    "mart_display_baseline": (
        "product_id, store_id, week",
        "product-store-week",
        "model estimate",
        "history windows exclude current row",
    ),
    "mart_incremental_effect": (
        "effect_id",
        "observed product-store-week effect estimate",
        "model_estimate",
        "confidence 0-1; model version required",
    ),
    "mart_allocation_candidates": (
        "candidate_id",
        "store-target week-position-category",
        "model estimate + simulated configuration",
        "compatibility explicit; source/version required",
    ),
    "mart_allocation_recommendations": (
        "recommendation_id",
        "store-target week-resource position",
        "scenario simulation",
        "one assignment per position; solver status required",
    ),
    "mart_space_audit": (
        "audit_id",
        "audit event",
        "simulated",
        "recommendation traceability; duplicate position check",
    ),
}

DESCRIPTIONS = {
    "source_record_id": "Stable demo source-row identifier.",
    "household_id": "Anonymous household identifier.",
    "store_id": "Anonymous store identifier.",
    "basket_id": "Anonymous shopping occasion identifier.",
    "product_id": "Anonymous product identifier.",
    "quantity": "Purchased unit count.",
    "sales_value": "Retailer sales amount in source currency.",
    "retail_disc": "Retail loyalty discount.",
    "coupon_disc": "Manufacturer coupon discount.",
    "coupon_match_disc": "Retailer coupon-match discount.",
    "week": "Source retail week, 1-53.",
    "transaction_timestamp": "Source purchase timestamp.",
    "data_source": "Provenance label separating real, estimated, derived, and simulated data.",
    "display_location": "Official display location code.",
    "mailer_location": "Official mailer position code.",
    "manufacturer_id": "Anonymous manufacturer identifier.",
    "department": "Product department.",
    "brand": "Private or national brand label in source.",
    "product_category": "Product category.",
    "product_type": "Lowest-level source product type.",
    "package_size": "Source package-size text.",
    "display_name": "Human-readable display name.",
    "display_group": "Display grouping.",
    "is_special_display": "Whether code denotes an extra/special display.",
    "retail_quarter": "Derived 13-week quarter.",
    "week_in_quarter": "Derived week within quarter.",
    "holiday_period": "Derived late-year holiday flag.",
    "raw_record_count": "Number of source promotion rows at resolved grain.",
    "actual_sales": "Observed aggregated sales; descriptive.",
    "units": "Observed aggregated quantity.",
    "product_count": "Distinct products in group.",
    "product_week_observations": "Product-week row count.",
    "brand_count": "Distinct observed brand labels.",
    "sales_per_product": "Observed sales divided by distinct products.",
    "sales_per_unit": "Observed sales divided by units.",
    "store_efficiency_rank": "Within-store/week descriptive efficiency rank.",
    "cross_store_category_rank": "Same-category cross-store rank.",
    "sql_expected_sales": "Leakage-controlled historical moving baseline.",
    "sql_descriptive_residual": "Actual minus SQL moving baseline.",
    "baseline_version": "Baseline calculation version.",
    "effect_id": "Unique effect estimate identifier.",
    "expected_sales_without_special_display": "Model counterfactual prediction with display set to code 0.",
    "predicted_sales_with_observed_display": "Model prediction with observed display feature.",
    "predicted_incremental_sales": "Model-predicted difference, never actual realized lift.",
    "confidence": "Support-based model confidence score from 0 to 1.",
    "model_version": "Model lineage version.",
    "candidate_id": "Unique allocation candidate identifier.",
    "target_week": "Simulated planning week.",
    "resource_position": "Simulated position identifier; not a physical floor-plan coordinate.",
    "resource_type": "Display resource type/code.",
    "category": "Candidate product category.",
    "current_category": "Simulated current allocation.",
    "change_cost": "Simulated adjustment cost.",
    "dominant_brand": "Modal source brand label for category.",
    "min_facings_per_store": "Simulated minimum allocation policy.",
    "max_facings_per_store": "Simulated maximum allocation / category-concentration policy.",
    "strategic_weight": "Simulated headquarters strategic objective weight.",
    "is_headquarters_strategic": "Simulated headquarters retention flag.",
    "is_change": "Whether candidate differs from current simulation.",
    "support_n": "Number of effect rows supporting category-location estimate.",
    "is_compatible": "Simulated category-resource fit rule.",
    "recommendation_id": "Unique recommendation identifier.",
    "recommended_category": "Solver-selected category.",
    "reason_code": "Auditable recommendation reason.",
    "solver_status": "CP-SAT or fallback status.",
    "audit_id": "Unique simulated audit identifier.",
    "planned_category": "Recommended/planned category.",
    "observed_category": "Simulated field observation.",
    "planned_date": "Simulated planned execution date.",
    "audit_date": "Simulated audit date.",
    "photo_status": "Simulated photo evidence status.",
    "match_status": "Plan/observation match result.",
    "exception_reason": "Simulated exception reason.",
}


def main() -> None:
    con = connect(read_only=True)
    parts = [
        "# 数据字典 / Data Dictionary\n\n",
        "字段类型由构建后的 DuckDB 自动提取；来源口径见 `docs/data_sources_and_definitions.md`。\n\n",
    ]
    for table, (pk, grain, source, quality) in TABLE_META.items():
        cols = con.execute(f"describe {table}").df()
        parts += [
            f"## `{table}`\n\n",
            f"- **主键**：{pk}\n- **粒度**：{grain}\n- **来源**：{source}\n- **质量规则**：{quality}\n\n",
            "| 字段 | 类型 | 说明 |\n|---|---|---|\n",
        ]
        for row in cols.itertuples():
            desc = DESCRIPTIONS.get(
                row.column_name, row.column_name.replace("_", " ").capitalize() + "."
            )
            parts.append(f"| `{row.column_name}` | `{row.column_type}` | {desc} |\n")
        parts.append("\n")
    con.close()
    target = ROOT / "docs" / "data_dictionary.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("".join(parts), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
