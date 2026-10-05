#!/usr/bin/env python3
"""Download and convert the official Complete Journey package data.

Demo mode uses the package's bundled anonymous samples. Full mode downloads the
full RDS transaction/promotion files and is intentionally opt-in.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd
import rdata
import requests

from display_optimizer.config import DEMO, ROOT, ensure_dirs

BASE = "https://raw.githubusercontent.com/bradleyboehmke/completejourney/master/data"
FILES = {
    "products": "products.rda",
    "transactions": "transactions_sample.rda",
    "promotions": "promotions_sample.rda",
}


def fetch(name: str, source_dir: Path | None) -> Path:
    cache = ROOT / "data" / "source_cache"
    cache.mkdir(parents=True, exist_ok=True)
    filename = FILES[name]
    target = cache / filename
    if target.exists():
        return target
    if source_dir:
        shutil.copy2(source_dir / filename, target)
        return target
    response = requests.get(f"{BASE}/{filename}", timeout=120)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def read_r_object(path: Path) -> pd.DataFrame:
    objects = rdata.read_rda(path)
    if len(objects) != 1:
        raise ValueError(f"Expected one object in {path}, found {list(objects)}")
    return next(iter(objects.values()))


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include=["category", "object"]).columns:
        out[col] = out[col].astype("string")
    return out


def build_demo(source_dir: Path | None = None) -> None:
    ensure_dirs()
    products = normalize(read_r_object(fetch("products", source_dir)))
    tx = normalize(read_r_object(fetch("transactions", source_dir)))
    promo = normalize(read_r_object(fetch("promotions", source_dir)))

    # Keep enough longitudinal and cross-store variation for a useful laptop demo.
    promotion_stores = promo["store_id"].astype(str).unique().tolist()
    top_transaction_stores = tx["store_id"].astype(str).value_counts().head(6).index.tolist()
    selected_stores = list(dict.fromkeys(promotion_stores + top_transaction_stores))
    tx = tx[tx["store_id"].astype(str).isin(selected_stores)].copy()
    joined = tx[["product_id"]].merge(
        products[["product_id", "product_category"]], on="product_id", how="left"
    )
    top_categories = joined["product_category"].value_counts().head(14).index
    keep_products = products.loc[products["product_category"].isin(top_categories), "product_id"]
    tx = tx[tx["product_id"].isin(keep_products)].copy()
    promo = promo[
        promo["store_id"].astype(str).isin(selected_stores)
        & promo["product_id"].isin(keep_products)
    ].copy()
    products = products[products["product_id"].isin(keep_products)].copy()

    tx["transaction_timestamp"] = pd.to_datetime(
        tx["transaction_timestamp"], unit="s", utc=True
    ).dt.tz_localize(None)
    tx.insert(0, "source_record_id", [f"TX{i:07d}" for i in range(len(tx))])
    for frame in (tx, promo, products):
        frame["data_source"] = "real_anonymized"

    tx.to_parquet(DEMO / "transactions.parquet", index=False)
    promo.to_parquet(DEMO / "promotions.parquet", index=False)
    products.to_parquet(DEMO / "products.parquet", index=False)
    print(
        f"Wrote official anonymous demo: {len(tx):,} transactions, "
        f"{len(promo):,} promotions, {len(products):,} products"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo"], default="demo")
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Optional local completejourney/data directory; avoids network access.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_demo(args.source_dir)
