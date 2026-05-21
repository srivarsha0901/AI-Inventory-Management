# ML Pipeline Step 1: Preprocessing + Feature Engineering

import pandas as pd
import numpy as np
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ================= CONFIG =================
RAW_DEMAND_DIR = "data/raw/favorita/"
OUT_DIR = "data/processed/"

os.makedirs(OUT_DIR, exist_ok=True)

# ================= LOAD DATA =================
def load_data():
    print("[1/5] Loading data...")

    # ── Optimized dtypes to reduce memory usage ──
    dtypes = {
        "id": "int32",
        "store_nbr": "int8",
        "item_nbr": "int32",
        "unit_sales": "float32",
        "onpromotion": "object",
    }

    row_limit = os.getenv("ML_TRAIN_ROWS", "20000000").strip().lower()
    row_limit = None if row_limit in {"", "all", "none"} else int(row_limit)

    # Load 20M rows by default -- 13x more than the old 1.5M limit.
    # The full 125M rows causes OOM during merge on machines with <16GB RAM.
    # 20M rows covers many product/store combinations with enough history
    # for lag features (28-day), rolling windows (30-day), and trend detection.
    train = pd.read_csv(
        os.path.join(RAW_DEMAND_DIR, "train.csv"),
        encoding="latin1",
        parse_dates=["date"],
        dtype=dtypes,
        nrows=row_limit,
    )

    print(f"  Loaded {len(train):,} rows")

    items = pd.read_csv(os.path.join(RAW_DEMAND_DIR, "items.csv"), encoding="latin1")
    stores = pd.read_csv(os.path.join(RAW_DEMAND_DIR, "stores.csv"), encoding="latin1")
    holidays = pd.read_csv(
        os.path.join(RAW_DEMAND_DIR, "holidays_events.csv"),
        encoding="latin1",
        parse_dates=["date"]
    )
    transactions = pd.read_csv(
        os.path.join(RAW_DEMAND_DIR, "transactions.csv"),
        encoding="latin1",
        parse_dates=["date"]
    )

    print(f"[OK] Train rows: {len(train):,}")

    return train, items, stores, holidays, transactions


# ================= CLEAN DATA =================
def clean_data(train):
    print("[2/5] Cleaning data...")

    train["unit_sales"] = train["unit_sales"].clip(lower=0)
    train["unit_sales"] = train["unit_sales"].fillna(0)

    train["onpromotion"] = train["onpromotion"].map({
        "True": 1, "False": 0, True: 1, False: 0
    }).fillna(0).astype(int)

    return train


# ================= MERGE =================
def merge_data(train, items, stores, holidays, transactions):
    print("[3/5] Merging datasets...")

    df = train.merge(items, on="item_nbr", how="left")
    df = df.merge(stores, on="store_nbr", how="left")
    df = df.merge(transactions, on=["date", "store_nbr"], how="left")

    holidays["is_holiday"] = 1
    holidays = holidays[["date", "is_holiday"]].drop_duplicates()

    df = df.merge(holidays, on="date", how="left")
    df["is_holiday"] = df["is_holiday"].fillna(0)

    return df


# ================= FEATURE ENGINEERING =================
def create_features(df):
    print("[4/5] Creating advanced features...")

    df = df.sort_values(["item_nbr", "store_nbr", "date"])

    # Time features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["dayofweek"] = df["date"].dt.dayofweek
    df["weekofyear"] = df["date"].dt.isocalendar().week.astype(int)
    df["quarter"] = df["date"].dt.quarter
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)

    # ═══════════════════════════════════════════════════════
    # 🔧 FIX: Apply log1p BEFORE computing lag/rolling features
    #    so that ALL features and the target are in the SAME
    #    log-scale. Previously, lags were raw-scale but rolling
    #    features were log-scale (inconsistent).
    # ═══════════════════════════════════════════════════════
    df["unit_sales"] = np.log1p(df["unit_sales"])

    # NOW compute features -- everything is in log-scale.
    # Keep every lag/rolling calculation inside each item/store series.
    # A plain rolling() after groupby().shift() can leak values across groups.
    grp = df.groupby(["item_nbr", "store_nbr"])["unit_sales"]

    # 🔥 LAG FEATURES (log-scale — consistent with target)
    df["lag_1"] = grp.shift(1)
    df["lag_7"] = grp.shift(7)
    df["lag_14"] = grp.shift(14)
    df["lag_21"] = grp.shift(21)
    df["lag_28"] = grp.shift(28)

    # 🔥 ROLLING MEAN (log-scale — consistent with target)
    df["rolling_mean_7"] = grp.transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).mean()
    )
    df["rolling_mean_14"] = grp.transform(
        lambda s: s.shift(1).rolling(14, min_periods=1).mean()
    )
    df["rolling_mean_30"] = grp.transform(
        lambda s: s.shift(1).rolling(30, min_periods=1).mean()
    )

    # 🔥 TREND COMPONENT (captures if product is growing/declining)
    def calculate_trend(x):
        x = np.asarray(x)
        if len(x) >= 7:
            try:
                z = np.polyfit(np.arange(len(x)), x, 1)
                return z[0]  # slope
            except:
                return 0
        return 0

    df["trend_30d"] = grp.transform(
        lambda s: s.shift(1).rolling(30, min_periods=7).apply(calculate_trend, raw=True)
    )
    df["trend_30d"] = df["trend_30d"].fillna(0)

    # 🔥 ROLLING STD (log-scale — consistent with target)
    df["rolling_std_7"] = grp.transform(
        lambda s: s.shift(1).rolling(7, min_periods=2).std()
    )
    df["rolling_std_14"] = grp.transform(
        lambda s: s.shift(1).rolling(14, min_periods=2).std()
    )

    # Fill missing values - better strategy for cold-start
    for col in [
        "lag_1","lag_7","lag_14","lag_21","lag_28",
        "rolling_mean_7","rolling_mean_14","rolling_mean_30",
        "rolling_std_7","rolling_std_14","trend_30d"
    ]:
        # For new products, use category average instead of just 0
        if col.startswith("lag_") or col.startswith("rolling_") or col == "trend_30d":
            df[col] = df.groupby("family")[col].transform(
                lambda x: x.fillna(x.mean())
            )
        df[col] = df[col].fillna(0)

    # Other features
    df["transactions"] = df["transactions"].fillna(0)

    df["family"] = df["family"].fillna("UNKNOWN")
    df["family_code"] = df["family"].astype("category").cat.codes

    df["perishable"] = df["perishable"].fillna(0)

    # ── Save family-code mapping for inference consistency ──
    family_map = df[["family", "family_code"]].drop_duplicates().set_index("family")["family_code"].to_dict()
    import json
    map_path = os.path.join(OUT_DIR, "family_code_map.json")
    with open(map_path, "w") as f:
        json.dump(family_map, f, indent=2)
    print(f"[OK] Family code mapping saved -> {map_path}")

    print(f"[OK] Final shape: {df.shape}")

    return df

# ================= MAIN =================
def main():
    train, items, stores, holidays, transactions = load_data()

    train = clean_data(train)

    df = merge_data(train, items, stores, holidays, transactions)

    df = create_features(df)

    # Save
    df.to_csv(os.path.join(OUT_DIR, "processed_demand.csv"), index=False)

    print("[DONE] Saved -> data/processed/processed_demand.csv")


if __name__ == "__main__":
    main()
