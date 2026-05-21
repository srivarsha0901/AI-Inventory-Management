import os

path = 'c:/Projects/AI Inventory Management/backend/routes/onboarding_routes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports if not present
if "load_inventory_name_index" not in content:
    import_block = "from product_matching import load_inventory_name_index, match_inventory_product, normalize_product_name, store_id_values\n"
    content = content.replace("import pytz", "import pytz\n" + import_block)

target_sales = """        now = datetime.now(timezone.utc)
        count = 0

        for _, row in df.iterrows():
            product_name = str(row.get("product_name") or row.get("product") or row.get("name", "")).strip()
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
        return jsonify({"message": f"Imported {count} sales records", "count": count})"""

replacement_sales = """        now = datetime.now(timezone.utc)
        inventory_index = load_inventory_name_index(db, store_id)
        count = 0
        matched_count = 0
        unmatched = []

        for _, row in df.iterrows():
            uploaded_name = str(
                row.get("product_name") or row.get("product") or row.get("name", "")
            ).strip()
            if not uploaded_name:
                continue

            # Check if there is a known synonym
            syn = db.product_synonyms.find_one({"store_id": store_id, "uploaded_name": uploaded_name})
            
            product_id = None
            inventory_id = None
            match_score = None
            
            if syn:
                product_name = syn["canonical_name"]
                product_id = syn.get("product_id")
                inventory_id = syn.get("inventory_id")
                match_score = 1.0
                matched_count += 1
            else:
                match = match_inventory_product(uploaded_name, inventory_index)
                if match:
                    product_name = match["canonical_name"]
                    inventory = match["inventory"]
                    product_id = inventory.get("product_id")
                    inventory_id = inventory.get("_id")
                    match_score = match["score"]
                    matched_count += 1
                else:
                    product_name = uploaded_name
                    unmatched.append(uploaded_name)

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
                    "uploaded_name": uploaded_name,
                    "product_id": str(product_id) if product_id else None,
                    "inventory_id": str(inventory_id) if inventory_id else None,
                    "match_score": match_score,
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
                {"store_id": {"$in": store_id_values(store_id)}, "product_name": product_name},
                {"$set": {"predicted_sales": qty, "last_updated": now}}
            )

        print(f"✅ Imported {count} sales records")
        unmatched_unique = sorted(set(unmatched))[:20]
        return jsonify({
            "message": f"Imported {count} sales records",
            "count": count,
            "matched_count": matched_count,
            "unmatched_count": len(set(unmatched)),
            "unmatched_products": unmatched_unique,
        })"""

if target_sales.replace('\\n', '\\r\\n') in content:
    content = content.replace(target_sales.replace('\\n', '\\r\\n'), replacement_sales.replace('\\n', '\\r\\n'))
else:
    content = content.replace(target_sales, replacement_sales)

# Add unmatched-sales route before parse-photo
unmatched_route = """

@onboarding_bp.route("/onboarding/unmatched-sales", methods=["GET"])
@jwt_required
def get_unmatched_sales_names():
    \"\"\"List uploaded sales product names that were not matched to inventory.\"\"\"
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        store_ids = store_id_values(store_id)

        pipeline = [
            {"$match": {"store_id": {"$in": store_ids}, "source": "historical_upload"}},
            {"$unwind": "$items"},
            {"$match": {
                "$or": [
                    {"items.match_score": None},
                    {"items.product_id": None},
                    {"items.product_id": ""},
                ]
            }},
            {"$group": {
                "_id": "$items.uploaded_name",
                "rows": {"$sum": 1},
                "total_qty": {"$sum": "$items.qty"},
                "last_seen": {"$max": "$created_at"},
            }},
            {"$sort": {"rows": -1}},
            {"$limit": 100},
        ]

        rows = []
        for row in db.sales.aggregate(pipeline):
            if not row.get("_id"):
                continue
            rows.append({
                "uploaded_name": row["_id"],
                "rows": row.get("rows", 0),
                "total_qty": row.get("total_qty", 0),
                "last_seen": row.get("last_seen").isoformat() if row.get("last_seen") else None,
            })

        return jsonify({"data": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"message": str(e)}), 500
"""

if "get_unmatched_sales_names" not in content:
    target_photo = "@onboarding_bp.route(\"/onboarding/parse-photo\", methods=[\"POST\"])"
    content = content.replace(target_photo, unmatched_route + "\\n" + target_photo)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Restored logic.")
