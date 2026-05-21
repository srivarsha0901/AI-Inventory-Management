# Inventory Optimization System (FINAL)

import pandas as pd
import numpy as np
import os

# ================= PATHS =================
PRED_PATH = "data/predictions/forecast_summary.csv"
GROCERY_PATH = "data/raw/grocery/Grocery_Inventory_and_Sales_Dataset.csv"
OUT_PATH = "data/predictions/reorder_plan.csv"

# ================= LOAD =================
print("📥 Loading predictions...")
pred = pd.read_csv(PRED_PATH)

print("📥 Loading grocery data...")
grocery = pd.read_csv(GROCERY_PATH)

# ================= CLEAN GROCERY =================
print("🧹 Cleaning grocery data...")

# Normalize column names
grocery.columns = grocery.columns.str.lower()

# Rename columns to match system
grocery.rename(columns={
    "product_id": "item_nbr",
    "stock_quantity": "stock"
}, inplace=True)

# ================= FIX DATA TYPES =================
print("🔧 Fixing data types...")

pred["item_nbr"] = pred["item_nbr"].astype(str)
grocery["item_nbr"] = grocery["item_nbr"].astype(str)

# ================= MERGE =================
print("🔗 Merging datasets...")

df = pred.merge(grocery, on="item_nbr", how="left")

# ================= HANDLE MISSING =================
# If stock missing → simulate realistic values
mask = df["stock"].isna()
df.loc[mask, "stock"] = (
    df.loc[mask, "predicted_sales"] * np.random.uniform(0.5, 1.5, size=mask.sum())
)

# ================= CALCULATIONS =================
print("⚙️ Calculating inventory decisions...")

# 🔧 FIX: Proper safety stock formula
#    safety_stock = z × σ_demand × √(lead_time_days)
#    z = 1.65 for 95% service level
SERVICE_LEVEL_Z = 1.65
DEFAULT_LEAD_TIME_DAYS = 3  # typical grocery restock lead time

# Use rolling std from predictions if available, else estimate from predicted_sales
if "demand_std" in df.columns:
    demand_std = df["demand_std"]
else:
    # Estimate: std ≈ 30% of mean demand (reasonable for grocery)
    demand_std = 0.30 * df["predicted_sales"]

df["safety_stock"] = (
    SERVICE_LEVEL_Z * demand_std * np.sqrt(DEFAULT_LEAD_TIME_DAYS)
).clip(lower=1)  # minimum 1 unit safety stock

# Reorder quantity
df["reorder_qty"] = (
    df["predicted_sales"] - df["stock"] + df["safety_stock"]
)

df["reorder_qty"] = df["reorder_qty"].clip(lower=0)

# Reorder flag
df["reorder_flag"] = df["reorder_qty"] > 0

# Stock status
def get_status(row):
    if row["stock"] == 0:
        return "Out of Stock"
    elif row["stock"] < row["predicted_sales"]:
        return "Low Stock"
    else:
        return "Sufficient"

df["stock_status"] = df.apply(get_status, axis=1)

# ================= SELECT IMPORTANT COLUMNS =================
final_cols = [
    "item_nbr",
    "predicted_sales",
    "stock",
    "safety_stock",
    "reorder_qty",
    "reorder_flag",
    "stock_status"
]

# Keep product name if available
if "product_name" in df.columns:
    final_cols.insert(1, "product_name")

df = df[final_cols]

# ================= SAVE =================
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

df.to_csv(OUT_PATH, index=False)

print("✅ Reorder plan saved → data/predictions/reorder_plan.csv")
print("🎉 Inventory optimization complete!")