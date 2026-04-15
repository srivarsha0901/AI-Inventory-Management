# ML Pipeline Step 3: Daily Prediction

import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime, timedelta

# ================= CONFIG =================
MODEL_PATH = "models/best_model.pkl"
DATA_PATH = "data/processed/processed_demand.csv"
OUT_DIR = "data/predictions"

os.makedirs(OUT_DIR, exist_ok=True)

# ================= LOAD MODEL =================
print("📥 Loading model...")
with open(MODEL_PATH, "rb") as f:
    bundle = pickle.load(f)

model = bundle["model"]
FEATURES = bundle["features"]

print(f"✅ Using model: {bundle['name']}")

# ================= LOAD DATA =================
print("📥 Loading processed data...")
df = pd.read_csv(DATA_PATH, parse_dates=["date"])

# ================= GET LATEST RECORD =================
latest = df.sort_values("date").groupby(["store_nbr", "item_nbr"]).tail(1)

print(f"✅ Latest records: {len(latest)}")

# ================= PREDICT FUTURE =================
print("🔮 Generating predictions...")

all_predictions = []

for day in range(7):  # next 7 days
    future_date = datetime.today() + timedelta(days=day)

    temp = latest.copy()

    # Update time features
    temp["month"] = future_date.month
    temp["dayofweek"] = future_date.weekday()
    temp["is_weekend"] = int(future_date.weekday() >= 5)

    # Predict (LOG scale)
    X = temp[FEATURES]
    preds = model.predict(X)

    # 🔥 Convert back to real sales
    preds = np.expm1(preds)

    temp["predicted_sales"] = preds
    temp["date"] = future_date

    all_predictions.append(
        temp[["date", "store_nbr", "item_nbr", "predicted_sales"]]
    )

# ================= FINAL OUTPUT =================
final_df = pd.concat(all_predictions)

# Summary per product
summary = final_df.groupby("item_nbr")["predicted_sales"].sum().reset_index()
summary = summary.sort_values("predicted_sales", ascending=False)

# Save files
final_df.to_csv(os.path.join(OUT_DIR, "predictions.csv"), index=False)
summary.to_csv(os.path.join(OUT_DIR, "forecast_summary.csv"), index=False)

print("✅ Predictions saved")
print("📊 predictions.csv + forecast_summary.csv created")