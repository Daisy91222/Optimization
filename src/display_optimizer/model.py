from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import OUTPUTS, SIMULATED, ensure_dirs
from .db import connect

MODEL_VERSION = "ridge_fe_v1"
CAT_COLS = ["store_id", "product_id", "category", "week", "mailer_location", "display_location"]
NUM_COLS = [
    "product_history_sales",
    "store_category_history_sales",
    "product_popularity",
    "retail_discount",
    "coupon_discount",
    "holiday_period",
]


def _pipeline() -> Pipeline:
    prep = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=2), CAT_COLS),
            ("num", StandardScaler(), NUM_COLS),
        ]
    )
    return Pipeline([("prep", prep), ("model", Ridge(alpha=8.0))])


def fit_baseline_and_candidates() -> dict:
    ensure_dirs()
    con = connect()
    features = con.execute("select * from mart_model_features order by week").df()
    if len(features) < 100:
        raise RuntimeError("Demo has too few model rows; rerun data preparation.")
    features[CAT_COLS] = features[CAT_COLS].fillna("UNKNOWN").astype(str)
    features[NUM_COLS] = features[NUM_COLS].fillna(0).astype(float)
    cutoff = int(features["week"].astype(int).quantile(0.8))
    train = features[features["week"].astype(int) <= cutoff]
    test = features[features["week"].astype(int) > cutoff]
    evaluation_model = _pipeline().fit(train[CAT_COLS + NUM_COLS], train["sales_value"])
    test_pred = evaluation_model.predict(test[CAT_COLS + NUM_COLS])
    metrics = {
        "model_version": MODEL_VERSION,
        "train_rows": len(train),
        "test_rows": len(test),
        "temporal_cutoff_week": cutoff,
        "mae": round(float(mean_absolute_error(test["sales_value"], test_pred)), 4),
        "r2": round(float(r2_score(test["sales_value"], test_pred)), 4),
        "interpretation": "predictive validation; not a causal identification result",
    }

    model = _pipeline().fit(features[CAT_COLS + NUM_COLS], features["sales_value"])
    actual_pred = model.predict(features[CAT_COLS + NUM_COLS])
    counterfactual = features.copy()
    counterfactual["display_location"] = "0"
    no_display_pred = model.predict(counterfactual[CAT_COLS + NUM_COLS])
    effects = features[["store_id", "week", "category", "display_location"]].copy()
    effects["actual_sales"] = features["sales_value"].to_numpy()
    effects["expected_sales_without_special_display"] = np.clip(no_display_pred, 0, None)
    effects["predicted_sales_with_observed_display"] = np.clip(actual_pred, 0, None)
    effects["predicted_incremental_sales"] = actual_pred - no_display_pred
    support = effects.groupby(["category", "display_location"])["category"].transform("size")
    effects["confidence"] = np.clip(np.log1p(support) / np.log(50), 0.15, 0.95)
    effects["model_version"] = MODEL_VERSION
    effects["data_source"] = "model_estimate"
    effects.insert(0, "effect_id", [f"EFF-{i + 1:07d}" for i in range(len(effects))])

    con.register("effect_df", effects)
    con.execute("create or replace table mart_incremental_effect as select * from effect_df")

    capacity = pd.read_parquet(SIMULATED / "resource_capacity.parquet").drop(
        columns=["data_source", "simulation_assumption"]
    )
    current = pd.read_parquet(SIMULATED / "current_allocation.parquet").drop(columns="data_source")
    compatible = pd.read_parquet(SIMULATED / "compatibility.parquet").drop(
        columns=["data_source", "rule_reason"]
    )
    policy = pd.read_parquet(SIMULATED / "category_policy.parquet").drop(columns="data_source")
    target_week = int(features["week"].astype(int).max()) + 1

    effect_lookup = (
        effects[effects["display_location"] != "0"]
        .groupby(["category", "display_location"], as_index=False)
        .agg(
            predicted_incremental_sales=("predicted_incremental_sales", "median"),
            confidence=("confidence", "max"),
            support_n=("effect_id", "count"),
        )
    )
    location_fallback = (
        effects[effects["display_location"] != "0"]
        .groupby("display_location", as_index=False)
        .agg(location_effect=("predicted_incremental_sales", "median"))
    )
    store_category = con.execute(
        """select store_id, product_category category, avg(sales_value) avg_sales
           from fact_store_week_category group by 1,2"""
    ).df()
    category_global = (
        store_category.groupby("category", as_index=False)["avg_sales"]
        .mean()
        .rename(columns={"avg_sales": "global_avg_sales"})
    )

    candidates = capacity.merge(policy, how="cross")
    candidates = candidates.merge(
        current,
        on=["store_id", "resource_type", "resource_position"],
        suffixes=("_capacity", "_current"),
    )
    candidates = candidates.merge(compatible, on=["resource_type", "category"])
    candidates = candidates.merge(
        effect_lookup,
        left_on=["category", "resource_type"],
        right_on=["category", "display_location"],
        how="left",
    ).merge(
        location_fallback,
        left_on="resource_type",
        right_on="display_location",
        how="left",
        suffixes=("", "_fallback"),
    )
    candidates = candidates.merge(store_category, on=["store_id", "category"], how="left").merge(
        category_global, on="category", how="left"
    )
    candidates["predicted_incremental_sales"] = (
        candidates["predicted_incremental_sales"].fillna(candidates["location_effect"]).fillna(0)
    )
    scale = (
        (candidates["avg_sales"].fillna(0) / candidates["global_avg_sales"].replace(0, np.nan))
        .fillna(1)
        .clip(0.5, 1.5)
    )
    candidates["predicted_incremental_sales"] *= 0.5 + 0.5 * scale
    candidates["confidence"] = candidates["confidence"].fillna(0.25)
    candidates["support_n"] = candidates["support_n"].fillna(0).astype(int)
    candidates["target_week"] = target_week
    candidates["model_version"] = MODEL_VERSION
    candidates["data_source"] = "model_estimate+simulated_configuration"
    candidates["candidate_id"] = [f"CAN-{i + 1:07d}" for i in range(len(candidates))]
    candidates["is_change"] = candidates["category"] != candidates["current_category"]
    keep = [
        "candidate_id",
        "store_id",
        "target_week",
        "resource_position",
        "resource_type",
        "category",
        "current_category",
        "predicted_incremental_sales",
        "confidence",
        "change_cost",
        "dominant_brand",
        "min_facings_per_store",
        "max_facings_per_store",
        "strategic_weight",
        "is_headquarters_strategic",
        "is_change",
        "support_n",
        "is_compatible",
        "model_version",
        "data_source",
    ]
    candidates = candidates[keep]
    con.register("candidate_df", candidates)
    con.execute("create or replace table mart_allocation_candidates as select * from candidate_df")
    con.close()
    (OUTPUTS / "model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
