# ML Pipeline Step 1: Preprocessing + Feature Engineering

import pandas as pd
import numpy as np
import os

# ================= CONFIG =================
RAW_DEMAND_DIR = "data/raw/favorita/"
OUT_DIR = "data/processed/"

os.makedirs(OUT_DIR, exist_ok=True)

# ================= LOAD DATA =================
def load_data():
    print("📥 Loading data...")

    train = pd.read_csv(
        os.path.join(RAW_DEMAND_DIR, "train.csv"),
        encoding="latin1",
        parse_dates=["date"],
        nrows=1500000  # Increased from 500K to 1.5M (3x more data for better accuracy!)
    )

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

    print(f"✅ Train rows: {len(train)}")

    return train, items, stores, holidays, transactions


# ================= CLEAN DATA =================
def clean_data(train):
    print("🧹 Cleaning data...")

    train["unit_sales"] = train["unit_sales"].clip(lower=0)
    train["unit_sales"] = train["unit_sales"].fillna(0)

    train["onpromotion"] = train["onpromotion"].map({
        "True": 1, "False": 0, True: 1, False: 0
    }).fillna(0).astype(int)

    return train


# ================= MERGE =================
def merge_data(train, items, stores, holidays, transactions):
    print("🔗 Merging datasets...")

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
    print("⚙️ Creating advanced features...")

    df = df.sort_values(["item_nbr", "store_nbr", "date"])

    # Time features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["dayofweek"] = df["date"].dt.dayofweek
    df["weekofyear"] = df["date"].dt.isocalendar().week.astype(int)
    df["quarter"] = df["date"].dt.quarter
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)

    grp = df.groupby(["item_nbr", "store_nbr"])["unit_sales"]

    # 🔥 LAG FEATURES
    df["lag_1"] = grp.shift(1)
    df["lag_7"] = grp.shift(7)
    df["lag_14"] = grp.shift(14)
    df["lag_21"] = grp.shift(21)
    df["lag_28"] = grp.shift(28)
    df["unit_sales"] = np.log1p(df["unit_sales"])
    # 🔥 ROLLING MEAN
    df["rolling_mean_7"] = grp.shift(1).rolling(7).mean()
    df["rolling_mean_14"] = grp.shift(1).rolling(14).mean()
    df["rolling_mean_30"] = grp.shift(1).rolling(30).mean()
    
    # 🔥 TREND COMPONENT (new feature for better forecasting)
    def calculate_trend(x):
        if len(x) >= 7:
            try:
                z = np.polyfit(np.arange(len(x)), x.values, 1)
                return z[0]  # slope
            except:
                return 0
        return 0
    
    df["trend_30d"] = grp.shift(1).rolling(30, min_periods=7).apply(calculate_trend, raw=False)
    df["trend_30d"] = df["trend_30d"].fillna(0)

    # 🔥 ROLLING STD (VERY IMPORTANT)
    df["rolling_std_7"] = grp.shift(1).rolling(7).std()
    df["rolling_std_14"] = grp.shift(1).rolling(14).std()

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

    print(f"✅ Final shape: {df.shape}")

    return df

# ================= MAIN =================
def main():
    train, items, stores, holidays, transactions = load_data()

    train = clean_data(train)

    df = merge_data(train, items, stores, holidays, transactions)

    df = create_features(df)

    # Save
    df.to_csv(os.path.join(OUT_DIR, "processed_demand.csv"), index=False)

    print("✅ Saved → data/processed/processed_demand.csv")


if __name__ == "__main__":
    main()