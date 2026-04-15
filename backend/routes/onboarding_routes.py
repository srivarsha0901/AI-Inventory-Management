from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
import pandas as pd
import pytz

onboarding_bp = Blueprint("onboarding", __name__)


@onboarding_bp.route("/onboarding/inventory", methods=["POST"])
@jwt_required
def save_inventory():
    try:
        db       = get_db()
        data     = request.get_json()
        items    = data.get("items", [])
        user     = request.current_user
        store_id = user.get("store_id")

        if not items:
            return jsonify({"message": "No items provided"}), 400

        now = datetime.now(timezone.utc)

        for item in items:
            if not item.get("name", "").strip():
                continue

            stock        = int(item.get("stock") or 0)
            safety       = int(item.get("safety_stock") or 10)
            restock_days = int(item.get("restock_days") or 7)
            reorder_point = safety + 5
            status = (
                "Out of Stock" if stock == 0 else
                "Low Stock" if stock <= reorder_point else
                "Healthy"
            )

            shelf_life = int(item.get("shelf_life_days") or 0)

            product = {
                "name":          item["name"].strip(),
                "sku":           f"{store_id}-{item['name'].strip().upper().replace(' ', '-')}",
                "category":      item.get("category", "General"),
                "unit":          item.get("unit", "units"),
                "cost_price":    float(item.get("cost_price") or 0),
                "selling_price": float(item.get("selling_price") or 0),
                "shelf_life_days": shelf_life,
                "emoji":         item.get("emoji", "📦"),
                "safety_stock":  safety,
                "reorder_point": reorder_point,
                "restock_days":  restock_days,
                "store_id":      store_id,
                "is_active":     True,
                "created_at":    now,
            }

            result  = db.products.update_one(
                {"sku": product["sku"]},
                {"$set": product},
                upsert=True
            )
            prod_id = result.upserted_id or db.products.find_one({"sku": product["sku"]})["_id"]

            db.inventory.update_one(
                {"store_id": store_id, "product_name": item["name"].strip()},
                {"$set": {
                    "product_id":      prod_id,
                    "product_name":    item["name"].strip(),
                    "sku":             product["sku"],
                    "category":        product["category"],
                    "emoji":           product["emoji"],
                    "unit":            product["unit"],
                    "cost_price":      product["cost_price"],
                    "selling_price":   product["selling_price"],
                    "shelf_life_days": shelf_life,
                    "stock":           stock,
                    "predicted_sales": 0,
                    "safety_stock":    safety,
                    "reorder_point":   reorder_point,
                    "restock_days":    restock_days,
                    "stock_status":    status,
                    "store_id":        store_id,
                    "last_updated":    now,
                }},
                upsert=True
            )

            if status in ("Low Stock", "Out of Stock"):
                existing = db.alerts.find_one({
                    "product_name": item["name"].strip(),
                    "store_id":     store_id,
                    "status":       "active",
                })
                if not existing:
                    db.alerts.insert_one({
                        "product_name": item["name"].strip(),
                        "type":         "low_stock",
                        "message":      f"{stock} {product['unit']} left — below reorder point of {reorder_point}",
                        "severity":     "critical" if status == "Out of Stock" else "warning",
                        "status":       "active",
                        "store_id":     store_id,
                        "created_at":   now,
                    })

        return jsonify({"message": f"Saved {len(items)} products successfully"})

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@onboarding_bp.route("/onboarding/parse-file", methods=["POST"])
@jwt_required
def parse_file():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"message": "No file uploaded"}), 400

        filename = file.filename.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

        items = []
        for _, row in df.iterrows():
            items.append({
                "name":         str(row.get("name") or row.get("product_name") or row.get("item", "")).strip(),
                "category":     str(row.get("category", "General")),
                "unit":         str(row.get("unit", "units")),
                "cost_price":    str(row.get("cost_price") or row.get("cp") or "0"),
                "selling_price": str(row.get("selling_price") or row.get("price") or "0"),
                "stock":        str(row.get("stock") or row.get("quantity") or row.get("qty", "0")),
                "safety_stock": str(row.get("safety_stock") or row.get("min_stock", "10")),
                "restock_days": str(row.get("restock_days") or "7"),
                "emoji":        "📦",
            })

        items = [i for i in items if i["name"]]
        return jsonify({"items": items})

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@onboarding_bp.route("/onboarding/parse-sales", methods=["POST"])
@jwt_required
def parse_sales_history():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        file     = request.files.get("file")

        print("📥 Sales upload received, store:", store_id)

        if not file:
            return jsonify({"message": "No file uploaded"}), 400

        filename = file.filename.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        print("Columns:", df.columns.tolist())
        print("Rows:", len(df))

        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

        now   = datetime.now(timezone.utc)
        count = 0

        for _, row in df.iterrows():
            product_name = str(
                row.get("product_name") or row.get("product") or row.get("name", "")
            ).strip()
            if not product_name:
                continue

            try:
                sale_date = pd.to_datetime(row.get("date", now)).to_pydatetime()
                if sale_date.tzinfo is None:
                    sale_date = pytz.utc.localize(sale_date)
            except:
                sale_date = now

            qty   = float(row.get("qty_sold") or row.get("qty") or 1)
            price = float(row.get("unit_price") or row.get("price") or 0)
            total = float(row.get("total") or qty * price)

            db.sales.insert_one({
                "store_id":     store_id,
                "cashier_id":   request.current_user.get("sub"),
                "product_name": product_name,
                "items": [{
                    "name":       product_name,
                    "qty":        qty,
                    "unit_price": price,
                }],
                "subtotal":   total,
                "tax":        0,
                "total":      total,
                "source":     "historical_upload",
                "created_at": sale_date,
            })
            count += 1

            db.inventory.update_one(
                {"store_id": store_id, "product_name": product_name},
                {"$set": {"predicted_sales": qty, "last_updated": now}}
            )

        print(f"✅ Imported {count} sales records")
        return jsonify({"message": f"Imported {count} sales records", "count": count})

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"message": str(e)}), 500


@onboarding_bp.route("/onboarding/parse-photo", methods=["POST"])
@jwt_required
def parse_photo():
    """OCR a photo of inventory/invoice and extract product list."""
    try:
        file = request.files.get("image")
        if not file:
            return jsonify({"message": "No image uploaded"}), 400

        # Read image bytes
        image_bytes = file.read()
        
        # Try to extract text using OCR
        from ocr_routes import _extract_text_from_image, _parse_invoice_text
        
        raw_text = _extract_text_from_image(image_bytes)
        if not raw_text:
            # Fallback: return error (OCR libraries not installed)
            return jsonify({
                "message": "OCR not available. Please use manual entry or CSV upload.",
                "items": []
            }), 200
        
        # Parse the extracted text
        parsed_items = _parse_invoice_text(raw_text)
        
        # Convert to inventory item format
        items = []
        for parsed in parsed_items:
            items.append({
                "name":         parsed.get("name", "").strip(),
                "category":     "General",
                "unit":         parsed.get("unit", "units"),
                "cost_price":   str(parsed.get("price", 0)),
                "selling_price": str(parsed.get("price", 0) * 1.5),  # Estimate 50% markup
                "stock":        str(parsed.get("qty", 0)),
                "safety_stock": "10",
                "restock_days": "7",
                "emoji":        "📦",
            })
        
        items = [i for i in items if i["name"]]
        return jsonify({"items": items})

    except Exception as e:
        return jsonify({"message": f"Photo parsing error: {str(e)}"}), 400