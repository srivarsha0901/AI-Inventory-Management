import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime, timedelta
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "best_model.pkl"))
print("Model path:", MODEL_PATH)
print("Model exists:", os.path.exists(MODEL_PATH))

def predict_for_store(sales_records, store_id):
    """
    sales_records: list of dicts with keys:
        product_name, qty_sold, date
    store_id: string
    
    Returns: list of dicts with product_name + predicted_sales
    """

    print(f"🔮 Predicting for store: {store_id}")

    # Load model
    with open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
    model    = bundle["model"]
    FEATURES = bundle["features"]

    # Build dataframe from sales records
    df = pd.DataFrame(sales_records)
    df["date"]     = pd.to_datetime(df["date"])
    df["qty_sold"] = pd.to_numeric(df["qty_sold"], errors="coerce").fillna(0)

    # Encode product names as item codes
    df["item_nbr"] = df["product_name"].astype("category").cat.codes

    df = df.sort_values(["item_nbr", "date"])

    # ── Build the same features your Kaggle model expects ──
    grp = df.groupby("item_nbr")["qty_sold"]

    df["lag_1"]  = grp.shift(1).fillna(0)
    df["lag_7"]  = grp.shift(7).fillna(0)
    df["lag_14"] = grp.shift(14).fillna(0)
    df["lag_21"] = grp.shift(21).fillna(0)
    df["lag_28"] = grp.shift(28).fillna(0)

    df["rolling_mean_7"]  = grp.shift(1).rolling(7,  min_periods=1).mean().fillna(0)
    df["rolling_mean_14"] = grp.shift(1).rolling(14, min_periods=1).mean().fillna(0)
    df["rolling_mean_30"] = grp.shift(1).rolling(30, min_periods=1).mean().fillna(0)
    df["rolling_std_7"]   = grp.shift(1).rolling(7,  min_periods=1).std().fillna(0)
    df["rolling_std_14"]  = grp.shift(1).rolling(14, min_periods=1).std().fillna(0)

    # 🔥 TREND component - captures if product is growing/declining
    def calc_trend(x):
        if len(x) >= 7:
            try:
                z = np.polyfit(np.arange(len(x)), x, 1)
                return z[0]
            except:
                return 0
        return 0
    df["trend_30d"] = grp.shift(1).rolling(30, min_periods=7).apply(calc_trend, raw=True).fillna(0)

    df["month"]      = df["date"].dt.month
    df["dayofweek"]  = df["date"].dt.dayofweek
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["is_holiday"] = 0        # can enhance later
    df["transactions"] = df.groupby("date")["qty_sold"].transform("sum")
    df["family_code"]  = df["item_nbr"]   # proxy
    df["perishable"]   = 1                # grocery = perishable

    # Get latest record per product
    latest = df.sort_values("date").groupby("item_nbr").tail(1).copy()

    predictions = []
    for day in range(7):
        future = datetime.today() + timedelta(days=day)
        temp   = latest.copy()

        temp["month"]      = future.month
        temp["dayofweek"]  = future.weekday()
        temp["is_weekend"] = int(future.weekday() >= 5)

        # Fill any missing features with 0
        for f in FEATURES:
            if f not in temp.columns:
                temp[f] = 0

        X     = temp[FEATURES]
        preds = model.predict(X)
        preds = np.expm1(preds)  # reverse log1p

        for i, row in temp.iterrows():
            product = df[df["item_nbr"] == row["item_nbr"]]["product_name"].iloc[0]
            predictions.append({
                "product_name":    product,
                "day_offset":      day,
                "date":            future.strftime("%Y-%m-%d"),
                "predicted_sales": max(0, round(float(preds[list(temp.index).index(i)]), 2))
            })

    # Summarize — avg daily prediction per product
    pred_df  = pd.DataFrame(predictions)
    summary  = pred_df.groupby("product_name")["predicted_sales"].mean().reset_index()
    summary.columns = ["product_name", "predicted_sales"]

    print(f"✅ Predictions for {len(summary)} products")
    return summary.to_dict(orient="records")


if __name__ == "__main__":
    # Test with sample data
    sample = [
        {"product_name": "Full Cream Milk", "qty_sold": 12, "date": "2026-03-01"},
        {"product_name": "Full Cream Milk", "qty_sold": 15, "date": "2026-03-02"},
        {"product_name": "Full Cream Milk", "qty_sold": 10, "date": "2026-03-03"},
        {"product_name": "Croissant",       "qty_sold": 8,  "date": "2026-03-01"},
        {"product_name": "Croissant",       "qty_sold": 10, "date": "2026-03-02"},
        {"product_name": "Croissant",       "qty_sold": 6,  "date": "2026-03-03"},
    ]
    result = predict_for_store(sample, "test_store")
    for r in result:
        print(r)