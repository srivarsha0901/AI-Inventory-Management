# ML Pipeline Step 2: FULL Model Comparison

import pandas as pd
import numpy as np
import os
import pickle

from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

# ================= CONFIG =================
DATA_PATH = "data/processed/processed_demand.csv"
MODEL_DIR = "models"

os.makedirs(MODEL_DIR, exist_ok=True)

# ================= LOAD =================
print("📥 Loading data...")
df = pd.read_csv(DATA_PATH)

FEATURES = [
    "lag_1","lag_7","lag_14","lag_21","lag_28",
    "rolling_mean_7","rolling_mean_14","rolling_mean_30",
    "rolling_std_7","rolling_std_14",
    "month","dayofweek","is_weekend",
    "is_holiday","transactions",
    "family_code","perishable","trend_30d"
]

TARGET = "unit_sales"

X = df[FEATURES]
y = df[TARGET]

print(f"✅ Data shape: {X.shape}")

# ================= SPLIT =================
tscv = TimeSeriesSplit(n_splits=3)

# ================= MODELS =================
models = {
    "XGBoost": XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        verbosity=0
    ),

    "LightGBM": LGBMRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1
    ),

    "CatBoost": CatBoostRegressor(
        iterations=100,
        depth=6,
        learning_rate=0.1,
        verbose=0
    )
}

results = {}

# ================= TRAIN =================
print("\n🚀 Training models...")

for name, model in models.items():
    print(f"\n🔹 Training {name}...")

    rmse_scores = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        preds = model.predict(X_val)

        rmse = np.sqrt(mean_squared_error(y_val, preds))
        rmse_scores.append(rmse)

    avg_rmse = np.mean(rmse_scores)
    results[name] = avg_rmse

    print(f"   RMSE: {avg_rmse:.4f}")

# ================= SAVE RESULTS =================
results_df = pd.DataFrame(list(results.items()), columns=["Model", "RMSE"])
results_df = results_df.sort_values("RMSE")

results_df.to_csv(os.path.join(MODEL_DIR, "model_comparison.csv"), index=False)

# ================= BEST MODEL =================
best_model_name = results_df.iloc[0]["Model"]
best_model = models[best_model_name]

print(f"\n🏆 Best Model: {best_model_name}")

# Train on full data
best_model.fit(X, y)

# Save model
bundle = {
    "model": best_model,
    "features": FEATURES,
    "name": best_model_name
}

with open(os.path.join(MODEL_DIR, "best_model.pkl"), "wb") as f:
    pickle.dump(bundle, f)

print("✅ Model saved")
print("📊 Results saved → models/model_comparison.csv")