# ML Pipeline Step 2: FULL Model Comparison
# Fixes: date-based CV split, MAPE/MAE metrics, more estimators

import pandas as pd
import numpy as np
import os
import pickle
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error

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

# ── Ensure date column is available for proper time-based splitting ──
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"📅 Date range: {df['date'].min()} → {df['date'].max()}")
else:
    print("⚠️ No date column found — falling back to index-based split")

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

history_feature_cols = [
    "lag_1","lag_7","lag_14","lag_21","lag_28",
    "rolling_mean_7","rolling_mean_14","rolling_mean_30",
]
max_history_feature = X[history_feature_cols].abs().max().max()
if max_history_feature > 30:
    raise SystemExit(
        "\nProcessed data looks stale or incompatible: lag/rolling features are not log-scale.\n"
        "Run preprocessing again first:\n"
        "  cd \"C:\\Projects\\AI Inventory Management\\inventory-ai\"\n"
        "  ..\\.venv\\Scripts\\python.exe ml\\01_preprocess.py\n"
        "Then rerun:\n"
        "  ..\\.venv\\Scripts\\python.exe ml\\02_train_models.py\n"
        "\nIf preprocessing is too heavy, use a smaller row count first:\n"
        "  $env:ML_TRAIN_ROWS='5000000'; ..\\.venv\\Scripts\\python.exe ml\\01_preprocess.py\n"
    )


# ================= METRICS =================
def compute_metrics(y_true, y_pred):
    """Compute log-scale and business-scale forecast metrics."""
    # Log-scale metrics (what the model directly optimizes)
    rmse_log = np.sqrt(mean_squared_error(y_true, y_pred))
    mae_log = mean_absolute_error(y_true, y_pred)

    # Real-scale metrics (business-interpretable)
    y_true_real = np.expm1(y_true)
    y_pred_real = np.expm1(y_pred)

    rmse_real = np.sqrt(mean_squared_error(y_true_real, y_pred_real))
    mae_real = mean_absolute_error(y_true_real, y_pred_real)
    abs_error = np.abs(y_true_real - y_pred_real)
    signed_error = y_pred_real - y_true_real

    # MAPE — skip zeros to avoid division errors
    mask = y_true_real > 0.5  # only products with meaningful sales
    if mask.sum() > 0:
        mape = np.mean(abs_error[mask] / y_true_real[mask]) * 100
        smape = np.mean(
            2 * abs_error[mask] / (np.abs(y_true_real[mask]) + np.abs(y_pred_real[mask]) + 1e-9)
        ) * 100
    else:
        mape = np.nan
        smape = np.nan

    accuracy_pct = max(0, 100 - mape) if not np.isnan(mape) else np.nan
    wape = abs_error.sum() / max(y_true_real.sum(), 1e-9) * 100
    bias_pct = signed_error.sum() / max(y_true_real.sum(), 1e-9) * 100
    wape_accuracy_pct = max(0, 100 - wape)

    return {
        "rmse_log": rmse_log,
        "mae_log": mae_log,
        "rmse_real": rmse_real,
        "mae_real": mae_real,
        "mape": mape,
        "smape": smape,
        "wape": wape,
        "bias_pct": bias_pct,
        "accuracy_pct": accuracy_pct,
        "wape_accuracy_pct": wape_accuracy_pct,
    }


# ================= DATE-BASED CV SPLIT =================
# Fix: Use actual dates so we never leak future data into training

def date_based_splits(df, n_splits=3):
    """Create time-based train/val splits using actual dates."""
    if "date" not in df.columns:
        # Fallback: simple index-based split (60/20/20 pattern)
        n = len(df)
        split_size = n // (n_splits + 1)
        splits = []
        for i in range(n_splits):
            train_end = split_size * (i + 1)
            val_end = train_end + split_size
            train_idx = np.arange(0, train_end)
            val_idx = np.arange(train_end, min(val_end, n))
            splits.append((train_idx, val_idx))
        return splits

    dates = df["date"].values
    unique_dates = np.sort(df["date"].unique())
    n_dates = len(unique_dates)
    split_size = n_dates // (n_splits + 1)

    splits = []
    for i in range(n_splits):
        train_cutoff = unique_dates[split_size * (i + 1)]
        val_cutoff = unique_dates[min(split_size * (i + 2), n_dates - 1)]

        train_idx = np.where(dates < train_cutoff)[0]
        val_idx = np.where((dates >= train_cutoff) & (dates < val_cutoff))[0]

        if len(val_idx) > 0:
            splits.append((train_idx, val_idx))

    return splits


splits = date_based_splits(df, n_splits=3)
print(f"✅ Created {len(splits)} date-based CV splits")

# ================= MODELS =================
models = {
    "XGBoost": XGBRegressor(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,
        reg_lambda=1.0,
        verbosity=0,
        n_jobs=-1,
    ),

    "LightGBM": LGBMRegressor(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=20,
        reg_alpha=0.1,
        reg_lambda=1.0,
        n_jobs=-1,
        verbose=-1,
    ),

    "CatBoost": CatBoostRegressor(
        iterations=300,
        depth=7,
        learning_rate=0.05,
        l2_leaf_reg=3,
        verbose=0,
    )
}

results = {}
baseline_results = {}

# ================= TRAIN =================
print("\n🚀 Training models...")

for name, model in models.items():
    print(f"\n🔹 Training {name}...")

    fold_metrics = []
    baseline_fold_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(splits):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        preds = model.predict(X_val)

        metrics = compute_metrics(y_val.values, preds)
        fold_metrics.append(metrics)

        # Same weekday last week is the benchmark the ML model should beat.
        baseline_preds = X_val["lag_7"].fillna(X_val["rolling_mean_7"]).fillna(0).values
        baseline_fold_metrics.append(compute_metrics(y_val.values, baseline_preds))

        print(f"   Fold {fold_idx+1}: RMSE={metrics['rmse_log']:.4f} | "
              f"MAPE={metrics['mape']:.1f}% | WAPE={metrics['wape']:.1f}%")

    # Average metrics across folds
    avg_metrics = {}
    for key in fold_metrics[0]:
        vals = [m[key] for m in fold_metrics if not np.isnan(m[key])]
        avg_metrics[key] = np.mean(vals) if vals else np.nan

    results[name] = avg_metrics

    avg_baseline_metrics = {}
    for key in baseline_fold_metrics[0]:
        vals = [m[key] for m in baseline_fold_metrics if not np.isnan(m[key])]
        avg_baseline_metrics[key] = np.mean(vals) if vals else np.nan
    baseline_results[name] = avg_baseline_metrics

    print(f"   -- AVG: RMSE={avg_metrics['rmse_log']:.4f} | "
          f"MAPE={avg_metrics['mape']:.1f}% | WAPE={avg_metrics['wape']:.1f}%")


# ================= SAVE RESULTS =================
results_rows = []
for name, metrics in results.items():
    results_rows.append({
        "Model": name,
        "RMSE_log": round(metrics["rmse_log"], 4),
        "MAE_log": round(metrics["mae_log"], 4),
        "RMSE_real": round(metrics["rmse_real"], 2),
        "MAE_real": round(metrics["mae_real"], 2),
        "MAPE": round(metrics["mape"], 2),
        "SMAPE": round(metrics["smape"], 2),
        "WAPE": round(metrics["wape"], 2),
        "Bias_pct": round(metrics["bias_pct"], 2),
        "Accuracy_pct": round(metrics["accuracy_pct"], 2),
        "WAPE_accuracy_pct": round(metrics["wape_accuracy_pct"], 2),
    })

results_df = pd.DataFrame(results_rows)
results_df = results_df.sort_values("RMSE_log")

results_df.to_csv(os.path.join(MODEL_DIR, "model_comparison.csv"), index=False)

baseline_rows = []
for name, metrics in baseline_results.items():
    baseline_rows.append({
        "Compared_Model": name,
        "Baseline": "lag_7_or_recent_mean",
        "RMSE_log": round(metrics["rmse_log"], 4),
        "MAE_log": round(metrics["mae_log"], 4),
        "RMSE_real": round(metrics["rmse_real"], 2),
        "MAE_real": round(metrics["mae_real"], 2),
        "MAPE": round(metrics["mape"], 2),
        "SMAPE": round(metrics["smape"], 2),
        "WAPE": round(metrics["wape"], 2),
        "Bias_pct": round(metrics["bias_pct"], 2),
        "Accuracy_pct": round(metrics["accuracy_pct"], 2),
        "WAPE_accuracy_pct": round(metrics["wape_accuracy_pct"], 2),
    })
baseline_df = pd.DataFrame(baseline_rows).sort_values("RMSE_log")
baseline_df.to_csv(os.path.join(MODEL_DIR, "baseline_comparison.csv"), index=False)

print("\n📊 Model Comparison:")
print(results_df.to_string(index=False))
print("\nBaseline Comparison:")
print(baseline_df.to_string(index=False))

# ================= BEST MODEL =================
best_model_name = results_df.iloc[0]["Model"]
best_model = models[best_model_name]

print(f"\n🏆 Best Model: {best_model_name}")

# ── Final holdout evaluation before saving ──
# Use last split's validation as the honest estimate
last_train_idx, last_val_idx = splits[-1]
best_model.fit(X.iloc[last_train_idx], y.iloc[last_train_idx])
holdout_preds = best_model.predict(X.iloc[last_val_idx])
holdout_metrics = compute_metrics(y.iloc[last_val_idx].values, holdout_preds)
print(f"   Holdout RMSE: {holdout_metrics['rmse_log']:.4f} | "
      f"MAPE: {holdout_metrics['mape']:.1f}% | WAPE: {holdout_metrics['wape']:.1f}%")

# Train final model on full data
print("🔄 Retraining best model on full data...")
best_model.fit(X, y)

# Save model
bundle = {
    "model": best_model,
    "features": FEATURES,
    "name": best_model_name,
    "metrics": {
        "rmse_log": float(results[best_model_name]["rmse_log"]),
        "mape": float(results[best_model_name]["mape"]),
        "smape": float(results[best_model_name]["smape"]),
        "wape": float(results[best_model_name]["wape"]),
        "bias_pct": float(results[best_model_name]["bias_pct"]),
        "accuracy_pct": float(results[best_model_name]["accuracy_pct"]),
        "wape_accuracy_pct": float(results[best_model_name]["wape_accuracy_pct"]),
    },
    "trained_at": pd.Timestamp.now().isoformat(),
}

with open(os.path.join(MODEL_DIR, "best_model.pkl"), "wb") as f:
    pickle.dump(bundle, f)

print("✅ Model saved → models/best_model.pkl")
print("📊 Results saved → models/model_comparison.csv")
