from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .config import SIMULATED, ensure_dirs
from .db import connect

RESOURCE_TYPES = ["1", "2", "3", "4", "5", "6", "7", "9"]


def _stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)


def generate_simulated_inputs(seed: int = 8451) -> None:
    """Create clearly labelled capacity/current-plan fields absent from source data."""
    ensure_dirs()
    rng = np.random.default_rng(seed)
    con = connect(read_only=True)
    stores = con.execute("select store_id from dim_store order by store_id").df()
    categories = con.execute(
        """
        select product_category as category, count(*) as n_products,
               mode(brand) as dominant_brand
        from dim_product where product_category is not null
        group by 1 order by n_products desc limit 12
        """
    ).df()
    max_week = int(con.execute("select max(week) from dim_week").fetchone()[0])
    con.close()

    category_list = categories["category"].tolist()
    positions = []
    current = []
    for store in stores["store_id"].astype(str):
        slot_counter = 0
        for code in RESOURCE_TYPES:
            capacity = 2 if code in {"3", "4", "5"} else 1
            for slot in range(1, capacity + 1):
                pos = f"{store}-{code}-{slot:02d}"
                positions.append(
                    {
                        "store_id": store,
                        "resource_type": code,
                        "resource_position": pos,
                        "capacity_units": 1,
                        "data_source": "simulated",
                        "simulation_assumption": "generic_demo_capacity_not_physical_floorplan",
                    }
                )
                idx = slot_counter % len(category_list)
                while (_stable_int(f"{code}|{category_list[idx]}") % 13) == 0:
                    idx = (idx + 1) % len(category_list)
                slot_counter += 1
                current.append(
                    {
                        "store_id": store,
                        "week": max_week,
                        "resource_position": pos,
                        "resource_type": code,
                        "current_category": category_list[idx],
                        "change_cost": round(float(rng.uniform(8, 35)), 2),
                        "data_source": "simulated",
                    }
                )

    compatibility = []
    for code in RESOURCE_TYPES:
        for category in category_list:
            # A deterministic sparse exclusion set demonstrates fit rules.
            allowed = (_stable_int(f"{code}|{category}") % 13) != 0
            compatibility.append(
                {
                    "resource_type": code,
                    "category": category,
                    "is_compatible": allowed,
                    "rule_reason": "demo_fit_rule" if not allowed else "eligible",
                    "data_source": "simulated",
                }
            )

    policy = categories.rename(columns={"product_category": "category"}).copy()
    policy["min_facings_per_store"] = 0
    policy["max_facings_per_store"] = 2
    policy["strategic_weight"] = 1.0
    if len(policy):
        policy.loc[policy.index[0], ["min_facings_per_store", "strategic_weight"]] = [1, 1.25]
    policy["is_headquarters_strategic"] = False
    if len(policy):
        policy.loc[policy.index[0], "is_headquarters_strategic"] = True
    policy["data_source"] = "simulated"

    pd.DataFrame(positions).to_parquet(SIMULATED / "resource_capacity.parquet", index=False)
    pd.DataFrame(current).to_parquet(SIMULATED / "current_allocation.parquet", index=False)
    pd.DataFrame(compatibility).to_parquet(SIMULATED / "compatibility.parquet", index=False)
    policy.to_parquet(SIMULATED / "category_policy.parquet", index=False)


def generate_audits(recommendations: pd.DataFrame, seed: int = 8451) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 7)
    rows = []
    for i, row in recommendations.iterrows():
        changed_observation = i % 7 == 0
        missing_photo = i % 11 == 0
        late = i % 9 == 0
        planned = row["recommended_category"]
        observed = row["current_category"] if changed_observation else planned
        planned_date = pd.Timestamp("2026-10-05")
        audit_date = planned_date + pd.Timedelta(days=int(rng.integers(0, 4)) + (4 if late else 0))
        rows.append(
            {
                "audit_id": f"AUD-{i + 1:05d}",
                "store_id": row["store_id"],
                "week": int(row["target_week"]),
                "resource_position": row["resource_position"],
                "planned_category": planned,
                "observed_category": observed,
                "planned_date": planned_date.date(),
                "audit_date": audit_date.date(),
                "photo_status": "missing" if missing_photo else "received",
                "match_status": "mismatch" if changed_observation else "matched",
                "exception_reason": "execution_mismatch" if changed_observation else None,
                "recommendation_id": row["recommendation_id"],
                "data_source": "simulated",
            }
        )
    audits = pd.DataFrame(rows)
    audits.to_parquet(SIMULATED / "space_audit.parquet", index=False)
    return audits
