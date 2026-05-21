import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime, timedelta

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "best_model.pkl"))
FAMILY_MAP_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed", "family_code_map.json"))
MIN_STRONG_HISTORY_DAYS = 28

print("Model path:", MODEL_PATH)
print("Model exists:", os.path.exists(MODEL_PATH))

# ── Category → Kaggle family mapping ──
# Maps common grocery categories to Kaggle Favorita's 'family' labels
# so family_code aligns with what the model learned during training.
CATEGORY_TO_FAMILY = {
    # Dairy & Eggs
    "dairy":      "DAIRY",
    "milk":       "DAIRY",
    "eggs":       "EGGS",
    "cheese":     "DAIRY",
    "yogurt":     "DAIRY",
    "butter":     "DAIRY",
    # Bakery
    "bakery":     "BREAD/BAKERY",
    "bread":      "BREAD/BAKERY",
    # Beverages
    "beverages":  "BEVERAGES",
    "drinks":     "BEVERAGES",
    "juice":      "BEVERAGES",
    "water":      "BEVERAGES",
    # Produce
    "fruits":     "PRODUCE",
    "vegetables": "PRODUCE",
    "produce":    "PRODUCE",
    # Meat & Seafood
    "meat":       "MEATS",
    "seafood":    "SEAFOOD",
    "poultry":    "POULTRY",
    "chicken":    "POULTRY",
    # Grocery staples
    "grocery":    "GROCERY I",
    "grains":     "GROCERY I",
    "rice":       "GROCERY I",
    "pasta":      "GROCERY I",
    "oils":       "GROCERY I",
    "spices":     "GROCERY I",
    "snacks":     "GROCERY II",
    "chips":      "GROCERY II",
    "sweets":     "GROCERY II",
    "candy":      "GROCERY II",
    # Frozen
    "frozen":     "FROZEN FOODS",
    # Cleaning
    "cleaning":   "HOME AND KITCHEN I",
    "household":  "HOME AND KITCHEN I",
    # Personal care
    "personal care": "PERSONAL CARE",
    "beauty":     "BEAUTY",
    # Default
    "general":    "GROCERY I",
}


def _load_family_code_map():
    """Load the family→code mapping saved during preprocessing."""
    if os.path.exists(FAMILY_MAP_PATH):
        with open(FAMILY_MAP_PATH, "r") as f:
            return json.load(f)
    return {}


def _get_family_code(category, family_map):
    """Convert a product category to the matching Kaggle family_code."""
    if not category:
        return family_map.get("GROCERY I", 0)

    cat_lower = category.lower().strip()

    # Direct match
    kaggle_family = CATEGORY_TO_FAMILY.get(cat_lower)
    if kaggle_family and kaggle_family in family_map:
        return family_map[kaggle_family]

    # Partial match
    for key, family in CATEGORY_TO_FAMILY.items():
        if key in cat_lower and family in family_map:
            return family_map[family]

    # Fallback to GROCERY I (most common category)
    return family_map.get("GROCERY I", 0)


def _prepare_daily_sales(sales_records):
    """Aggregate raw sales rows to a complete product/day time series."""
    df = pd.DataFrame(sales_records)
    if df.empty:
        return df

    df["product_name"] = df["product_name"].astype(str).str.strip()
    df = df[df["product_name"] != ""].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["qty_sold"] = pd.to_numeric(df["qty_sold"], errors="coerce").fillna(0)

    daily = (
        df.groupby(["product_name", "date"], as_index=False)
        .agg(qty_sold=("qty_sold", "sum"))
        .sort_values(["product_name", "date"])
    )

    filled = []
    for product, group in daily.groupby("product_name"):
        date_index = pd.date_range(group["date"].min(), group["date"].max(), freq="D")
        complete = (
            group.set_index("date")
            .reindex(date_index)
            .rename_axis("date")
            .reset_index()
        )
        complete["product_name"] = product
        complete["qty_sold"] = complete["qty_sold"].fillna(0)
        filled.append(complete)

    return pd.concat(filled, ignore_index=True)


def _build_store_baseline(daily_df):
    """Recent-demand baseline used to make predictions store-specific."""
    baselines = {}
    for product, group in daily_df.sort_values("date").groupby("product_name"):
        history = group["qty_sold"].astype(float).tail(MIN_STRONG_HISTORY_DAYS)
        if history.empty:
            baselines[product] = {"prediction": 0.0, "history_days": 0, "confidence": "low"}
            continue

        avg_7 = history.tail(7).mean()
        avg_28 = history.mean()
        trend = 0.0
        if len(history) >= 7:
            try:
                trend = np.polyfit(np.arange(len(history)), history.values, 1)[0]
            except Exception:
                trend = 0.0

        baseline = max(0.0, (0.7 * avg_7) + (0.3 * avg_28) + trend)
        active_sales_days = int((group["qty_sold"] > 0).sum())
        confidence = "high" if len(group) >= 28 and active_sales_days >= 14 else "medium" if len(group) >= 7 else "low"
        baselines[product] = {
            "prediction": float(baseline),
            "history_days": int(len(group)),
            "active_sales_days": active_sales_days,
            "confidence": confidence,
        }

    return baselines


def predict_for_store(sales_records, store_id, categories=None):
    """
    sales_records: list of dicts with keys:
        product_name, qty_sold, date
    store_id: string
    categories: optional dict mapping product_name → category string

    Returns: list of dicts with product_name + predicted_sales
    """

    print(f"Predicting for store: {store_id}")

    # Load model
    with open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
    model    = bundle["model"]
    FEATURES = bundle["features"]

    # Load family code mapping for consistent encoding
    family_map = _load_family_code_map()

    # Build a complete daily time series. Missing sales days matter for demand.
    df = _prepare_daily_sales(sales_records)
    if df.empty:
        return []

    store_baselines = _build_store_baseline(df)

    # Encode product names as item codes
    df["item_nbr"] = df["product_name"].astype("category").cat.codes

    df = df.sort_values(["item_nbr", "date"])

    # ═══════════════════════════════════════════════════════
    # 🔧 FIX: Apply log1p to qty_sold BEFORE computing features
    #    This matches the training pipeline where unit_sales is
    #    log-transformed before lag/rolling feature computation.
    # ═══════════════════════════════════════════════════════
    df["qty_sold_log"] = np.log1p(df["qty_sold"])

    grp = df.groupby("item_nbr")["qty_sold_log"]

    # Lag features (log-scale — matches training)
    df["lag_1"]  = grp.shift(1).fillna(0)
    df["lag_7"]  = grp.shift(7).fillna(0)
    df["lag_14"] = grp.shift(14).fillna(0)
    df["lag_21"] = grp.shift(21).fillna(0)
    df["lag_28"] = grp.shift(28).fillna(0)

    # Rolling features (log-scale — matches training)
    df["rolling_mean_7"] = grp.transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).mean()
    ).fillna(0)
    df["rolling_mean_14"] = grp.transform(
        lambda s: s.shift(1).rolling(14, min_periods=1).mean()
    ).fillna(0)
    df["rolling_mean_30"] = grp.transform(
        lambda s: s.shift(1).rolling(30, min_periods=1).mean()
    ).fillna(0)
    df["rolling_std_7"] = grp.transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).std()
    ).fillna(0)
    df["rolling_std_14"] = grp.transform(
        lambda s: s.shift(1).rolling(14, min_periods=1).std()
    ).fillna(0)

    # 🔥 TREND component — captures if product is growing/declining
    def calc_trend(x):
        if len(x) >= 7:
            try:
                z = np.polyfit(np.arange(len(x)), x, 1)
                return z[0]
            except:
                return 0
        return 0
    df["trend_30d"] = grp.transform(
        lambda s: s.shift(1).rolling(30, min_periods=7).apply(calc_trend, raw=True)
    ).fillna(0)

    df["month"]      = df["date"].dt.month
    df["dayofweek"]  = df["date"].dt.dayofweek
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    
    # Use 'holidays' library for Indian public holidays
    import holidays
    ind_holidays = holidays.India(years=df["date"].dt.year.unique().tolist())
    df["is_holiday"] = df["date"].apply(lambda d: int(d in ind_holidays))

    # 🔧 FIX: Use store-level transaction total (daily qty across all products)
    df["transactions"] = df.groupby("date")["qty_sold"].transform("sum")

    # 🔧 FIX: Map product categories to Kaggle family_codes for consistency
    if categories and family_map:
        df["family_code"] = df["product_name"].map(
            lambda name: _get_family_code(categories.get(name, "general"), family_map)
        )
    elif family_map:
        # No category info — use GROCERY I as default
        df["family_code"] = family_map.get("GROCERY I", 0)
    else:
        # No family map available — fallback to item_nbr (original behavior)
        df["family_code"] = df["item_nbr"]

    df["perishable"] = 1  # grocery default; can enhance with product metadata

    # Get latest record per product
    latest = df.sort_values("date").groupby("item_nbr").tail(1).copy()

    predictions = []
    for day in range(7):
        future = datetime.today() + timedelta(days=day)
        temp   = latest.copy()

        temp["month"]      = future.month
        temp["dayofweek"]  = future.weekday()
        temp["is_weekend"] = int(future.weekday() >= 5)
        temp["is_holiday"] = int(future in ind_holidays)

        # Fill any missing features with 0
        for f in FEATURES:
            if f not in temp.columns:
                temp[f] = 0

        X     = temp[FEATURES]
        preds = model.predict(X)
        preds = np.expm1(preds)  # reverse log1p

        for i, row in temp.iterrows():
            product = df[df["item_nbr"] == row["item_nbr"]]["product_name"].iloc[0]
            model_pred = max(0, float(preds[list(temp.index).index(i)]))
            baseline = store_baselines.get(
                product,
                {"prediction": model_pred, "history_days": 0, "confidence": "low"}
            )
            historical_weight = min(0.70, baseline.get("history_days", 0) / MIN_STRONG_HISTORY_DAYS)
            model_weight = 1 - historical_weight
            final_pred = (historical_weight * baseline["prediction"]) + (model_weight * model_pred)

            predictions.append({
                "product_name":    product,
                "day_offset":      day,
                "date":            future.strftime("%Y-%m-%d"),
                "predicted_sales": round(max(0, final_pred), 2),
                "model_predicted_sales": round(model_pred, 2),
                "baseline_predicted_sales": round(baseline["prediction"], 2),
                "confidence": baseline.get("confidence", "low"),
            })

    # Summarize — avg daily prediction per product
    pred_df  = pd.DataFrame(predictions)
    summary = (
        pred_df.groupby("product_name", as_index=False)
        .agg(
            predicted_sales=("predicted_sales", "mean"),
            model_predicted_sales=("model_predicted_sales", "mean"),
            baseline_predicted_sales=("baseline_predicted_sales", "mean"),
            confidence=("confidence", "first"),
        )
    )
    for col in ["predicted_sales", "model_predicted_sales", "baseline_predicted_sales"]:
        summary[col] = summary[col].round(2)

    print(f"Predictions for {len(summary)} products")
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
    categories = {
        "Full Cream Milk": "Dairy",
        "Croissant": "Bakery",
    }
    result = predict_for_store(sample, "test_store", categories=categories)
    for r in result:
        print(r)
