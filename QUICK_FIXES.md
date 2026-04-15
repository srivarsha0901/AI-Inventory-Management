# FreshTrack Audit - Quick Fixes Guide

## 🔴 CRITICAL: Must Fix Before Production (2-3 hours)

### 1. JWT store_id Bug (Breaks Multi-Store Safety)
```python
# FILE: backend/jwt_helper.py, Line 13

# WRONG - Creates unsafe string:
"store_id": str(user_doc.get("store_id", ""))  

# CORRECT - Keep as ObjectId in DB, string in JWT:
import bson
payload = {
    "sub": str(user_doc["_id"]),  # User always as string
    "store_id": str(user_doc.get("store_id", "")),  # Store always as string
    ...
}

# Then in routes, convert back:
store_id = ObjectId(request.current_user.get("store_id"))
```

---

### 2. Disable Debug Mode
```python
# FILE: backend/app.py, Line 41

import os

DEBUG = os.getenv("FLASK_ENV", "production") == "development"

if __name__ == "__main__":
    app.run(debug=DEBUG, port=5000)
```

---

### 3. Fix ML Model Path
```python
# FILE: backend/routes/ml_routes.py, Line 175-180

import os

ML_PATH = os.getenv("ML_MODEL_PATH")
if not ML_PATH:
    # Fallback based on project structure
    ML_PATH = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "inventory-ai", "ml"
    )

if not os.path.exists(ML_PATH):
    raise RuntimeError(f"ML models not found at {ML_PATH}")

# Remove sys.path.append() - use importlib instead
```

---

### 4. Implement _log() Function
```python
# FILE: backend/routes/staff_routes.py (add at top, line 50)

def _log(db, store_id, user_id, user_name, action, details):
    """Write to activity log."""
    try:
        db.activity_log.insert_one({
            "store_id": ObjectId(store_id) if isinstance(store_id, str) else store_id,
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "user_name": user_name,
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        print(f"⚠️ Activity log failed: {e}")  # Don't crash main flow
```

---

### 5. Fix POS ObjectId Bug
```python
# FILE: backend/routes/pos_routes.py, Line 48-56

for item in items:
    pid = item.get("product_id")
    qty = int(item.get("qty", 1))
    if not pid:
        continue

    try:
        # Try as ObjectId first
        inv = db.inventory.find_one({"product_id": ObjectId(pid)})
    except:
        # Fallback to string
        inv = db.inventory.find_one({"product_id": pid})
    
    if not inv:
        continue
    
    # REST OF CODE...
```

---

## 🟠 HIGH PRIORITY: Implement Missing Features (1-2 days)

### 6. Implement `/onboarding/parse-file`
```python
# FILE: backend/routes/onboarding_routes.py

@onboarding_bp.route("/onboarding/parse-file", methods=["POST"])
@jwt_required
def parse_file():
    from werkzeug.utils import secure_filename
    import pandas as pd
    import openpyxl
    
    file = request.files.get("file")
    if not file:
        return {"message": "No file uploaded"}, 400
    
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return {"message": "Format must be CSV or Excel"}, 400
        
        items = []
        for _, row in df.iterrows():
            items.append({
                "name": row.get("name", ""),
                "category": row.get("category", "General"),
                "unit": row.get("unit", "kg"),
                "cost_price": float(row.get("cost_price", 0)),
                "selling_price": float(row.get("selling_price", 0)),
                "shelf_life_days": int(row.get("shelf_life_days", 0)),
                "stock": float(row.get("stock", 0)),
                "safety_stock": int(row.get("safety_stock", 10)),
                "restock_days": int(row.get("restock_days", 7)),
                "emoji": row.get("emoji", "📦"),
            })
        
        return {"items": items}, 200
    except Exception as e:
        return {"message": f"Parse error: {str(e)}"}, 400
```

---

### 7. Implement `/onboarding/parse-photo`
```python
# FILE: backend/routes/onboarding_routes.py

@onboarding_bp.route("/onboarding/parse-photo", methods=["POST"])
@jwt_required
def parse_photo():
    import io
    from PIL import Image
    import pytesseract
    import re
    
    file = request.files.get("image")
    if not file:
        return {"message": "No image uploaded"}, 400
    
    try:
        img = Image.open(io.BytesIO(file.read()))
        text = pytesseract.image_to_string(img)
        
        # Parse lines like "Milk  32  L  42  62" or "Milk x 32 @ 42 = 1344"
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Try patterns
            match = re.search(r"(\w+)\s+(\d+)\s+(\w+)\s+(\d+)\s+(\d+)", line)
            if match:
                items.append({
                    "name": match.group(1),
                    "stock": float(match.group(2)),
                    "unit": match.group(3),
                    "cost_price": float(match.group(4)),
                    "selling_price": float(match.group(5)),
                    "category": "General",
                    "emoji": "📦",
                    "safety_stock": 10,
                    "restock_days": 7,
                })
        
        return {"items": items or [{"name": "Please verify manually"}]}, 200
    except Exception as e:
        return {"message": f"OCR failed: {str(e)}"}, 400
```

---

### 8. Fix Race Condition in POS
```python
# FILE: backend/routes/pos_routes.py (line 65-80)

# WRONG - Two-step read-then-write:
new_stock = max(0, inv.get("stock", 0) - qty)
db.inventory.update_one({"_id": inv["_id"]}, {"$set": {"stock": new_stock}})

# CORRECT - Atomic operation:
db.inventory.update_one(
    {"_id": inv["_id"]},
    {"$inc": {"stock": -qty}}  # Atomic decrement
)
```

---

## 🟡 MEDIUM PRIORITY: Improvements (3-5 days)

### 9. Fix Alert Deduplication
```python
# FILE: backend/routes/pos_routes.py (line 79)

# Should check for alerts within last hour
from datetime import timedelta

existing = db.alerts.find_one({
    "product_name": inv.get("product_name"),
    "status": "active",
    "store_id": store_id,
    "created_at": {"$gte": now - timedelta(hours=1)}
})
```

---

### 10. Add Input Validation
```python
# FILE: backend/routes/pos_routes.py (top of file)

from marshmallow import Schema, fields, ValidationError, validate

class SaleSchema(Schema):
    items = fields.List(
        fields.Dict(keys=fields.Str()),
        required=True,
        validate=validate.Length(min=1)
    )
    subtotal = fields.Float(validate=validate.Range(min=0))
    tax = fields.Float(validate=validate.Range(min=0))
    total = fields.Float(validate=validate.Range(min=0))

@pos_bp.route("/sales", methods=["POST"])
@jwt_required
def create_sale():
    schema = SaleSchema()
    try:
        validated = schema.load(request.get_json())
    except ValidationError as err:
        return {"message": err.messages}, 400
    
    # Use validated data instead of request.get_json()
```

---

### 11. Add Rate Limiting
```python
# FILE: backend/app.py

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Protect auth endpoints
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    ...
```

---

### 12. Fix Error Handling in ML
```python
# FILE: inventory-ai/ml/predict_for_store.py (line 20-30)

def predict_for_store(sales_records, store_id):
    if not sales_records or len(sales_records) < 3:
        return [
            {
                "product_name": "Insufficient Data",
                "predicted_sales": 0,
                "note": "Need 3+ days of sales history"
            }
        ]
    
    try:
        with open(MODEL_PATH, "rb") as f:
            bundle = pickle.load(f)
    except FileNotFoundError:
        return [{"product_name": "Model Error", "predicted_sales": 0}]
    
    # REST OF CODE...
```

---

## Environment Setup

Create `.env` file in backend/:
```bash
MONGO_URI=mongodb://localhost:27017/freshtrack
MONGO_DB_NAME=freshtrack
JWT_SECRET_KEY=your-secret-key-change-this
FLASK_ENV=development
ML_MODEL_PATH=/path/to/inventory-ai/models
CORS_ALLOW_ORIGINS=http://localhost:5173
```

---

## Testing Checklist

```bash
# After each fix, run:

# 1. Multi-store isolation test
curl -H "Authorization: Bearer <token1>" http://localhost:5000/api/inventory
curl -H "Authorization: Bearer <token2>" http://localhost:5000/api/inventory
# Both should only see their own store's inventory

# 2. JWT test
curl -H "Authorization: Bearer invalid_token" http://localhost:5000/api/dashboard/stats
# Should return 401 Unauthorized

# 3. POS concurrency test
# Simulate 2 concurrent sales for same product
# Stock should decrement correctly (not go negative)

# 4. ML predictions
curl -X POST http://localhost:5000/api/ml/run-predictions \
  -H "Authorization: Bearer <token>"
# Should work without crashing
```

