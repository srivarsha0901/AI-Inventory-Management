from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
import os
import sys
from datetime import datetime, timezone
from validation import ReorderDeliverySchema, ReorderSettingsSchema, validate_request
from transactions import TransactionManager, transaction_reorder_delivery

ml_bp = Blueprint("ml", __name__)

FORECAST_UNDERPREDICTION_BUFFER = 1.15




@ml_bp.route("/reorder/suggestions", methods=["GET"])
@jwt_required
def get_reorder():
    """Get reorder suggestions for low-stock products. Auto-creates reorder_orders."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId for DB queries
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id
        
        # Build query that works with both string and ObjectId store_id formats
        store_id_query = {"$in": [store_id, store_id_obj]} if store_id else {}
        query = {"store_id": store_id_query} if store_id else {}
        
        now      = datetime.now(timezone.utc)

        items = list(db.inventory.find({
            **query,
            "stock_status": {"$in": ["Low Stock", "Out of Stock"]}
        }))
        
        # Also include high-demand items with insufficient stock (matching alert criteria)
        high_demand_items = list(db.inventory.find({
            **query,
            "predicted_sales": {"$gte": 10},
            "$expr": {"$lt": ["$stock", {"$multiply": ["$predicted_sales", 3]}]}
        }))
        
        # Merge both lists, removing duplicates by product_name
        items_dict = {item["product_name"]: item for item in items}
        for item in high_demand_items:
            if item["product_name"] not in items_dict:
                items_dict[item["product_name"]] = item
        
        items = list(items_dict.values())

        suggestions = []
        for item in items:
            stock        = item.get("stock", 0)
            safety       = item.get("safety_stock", 10)
            reorder_pt   = item.get("reorder_point", safety + 5)
            predicted    = item.get("predicted_sales", 0)
            restock_days = item.get("restock_days", 7)
            shelf_life   = item.get("shelf_life_days", 0)
            cost_price   = item.get("cost_price", 0)
            selling_price = item.get("selling_price", 0)
            lead_time    = item.get("lead_time_days", 2)
            moq          = item.get("moq", 1)

            # Fallback: look up cost_price from products collection
            if (cost_price == 0 or not cost_price) and item.get("product_id"):
                try:
                    prod = db.products.find_one({"_id": item["product_id"]})
                    if prod:
                        cost_price    = prod.get("cost_price", 0)
                        selling_price = prod.get("selling_price", 0)
                        shelf_life    = prod.get("shelf_life_days", shelf_life)
                        lead_time     = prod.get("lead_time_days", lead_time)
                        moq           = prod.get("moq", moq)
                except:
                    pass
            
            # If still no cost_price, use a default to prevent errors
            if not cost_price or cost_price == 0:
                cost_price = 50  # Default fallback price

            # ── Smarter Reorder Calculation (Shelf-life, Lead Time, MOQ) ──
            if predicted > 0:
                # Calculate how many days worth of stock to order
                effective_restock = restock_days

                if shelf_life > 0:
                    # Cap restock days to shelf life — don't order more than can sell before expiry
                    effective_restock = min(restock_days, shelf_life)

                    # For perishable items (shelf_life <= 7), order smaller batches more often
                    if shelf_life <= 3:
                        effective_restock = min(effective_restock, 2)  # Max 2 days stock
                    elif shelf_life <= 7:
                        effective_restock = min(effective_restock, 4)  # Max 4 days stock

                # Reorder Point = Demand during lead time + safety stock
                dynamic_reorder_pt = int(predicted * lead_time) + safety
                # Target stock level after delivery
                target = dynamic_reorder_pt + int(predicted * effective_restock)
                
                # Check if we need to order (stock is below the dynamic reorder point)
                if stock <= dynamic_reorder_pt:
                    reorder_qty = max(target - stock, moq)
                else:
                    reorder_qty = 0
            else:
                if stock <= reorder_pt:
                    reorder_qty = max(reorder_pt + safety - stock, moq)
                    # If shelf life is very short and no prediction, keep orders small
                    if shelf_life > 0 and shelf_life <= 3:
                        reorder_qty = min(reorder_qty, safety * 2)
                else:
                    reorder_qty = 0

            urgency = (
                "critical" if stock == 0 else
                "critical" if safety > 0 and stock < safety * 0.5 else
                "high"     if stock < safety else
                "medium"
            )

            est_cost = reorder_qty * cost_price

            # Check if a reorder order for this product already exists (pending/approved)
            existing_order = db.reorder_orders.find_one({
                "store_id": {"$in": [store_id, store_id_obj]},
                "product_id": item.get("product_id"),
                "status": {"$in": ["pending", "approved"]}
            })

            suggestion_dict = {
                "id":             str(item["_id"]),
                "product_name":   item.get("product_name", "Unknown"),
                "emoji":          item.get("emoji", "📦"),
                "category":       item.get("category", "General"),
                "stock":          stock,
                "safety_stock":   safety,
                "reorder_point":  reorder_pt,
                "reorder_qty":    reorder_qty,
                "restock_days":   restock_days,
                "shelf_life_days": shelf_life,
                "unit":           item.get("unit", "units"),
                "unit_price":     cost_price,
                "selling_price":  selling_price,
                "stock_status":   item.get("stock_status"),
                "cost_price":     cost_price,
                "urgency":        urgency,
                "est_cost":       est_cost,
                "seasonal_boost": item.get("seasonal_boost"),
                "shelf_note":     (f"⚡ Perishable — order max {min(restock_days, shelf_life) if shelf_life else restock_days} days supply"
                                   if shelf_life and shelf_life <= 7 else ""),
                "has_pending_order": bool(existing_order)
            }
            
            suggestions.append(suggestion_dict)
            
            # Create reorder_order if one doesn't already exist (pending/approved)
            if not existing_order:
                try:
                    db.reorder_orders.insert_one({
                        "store_id":    store_id_obj,
                        "product_id":  item.get("product_id"),
                        "product_name": item.get("product_name", "Unknown"),
                        "reorder_qty": reorder_qty,
                        "unit":        item.get("unit", "units"),
                        "cost_price":  cost_price,
                        "est_cost":    est_cost,
                        "urgency":     urgency,
                        "status":      "pending",  # pending | approved | dismissed | delivered
                        "created_at":  now,
                    })
                except Exception as e:
                    print(f"⚠️ Failed to create reorder order: {e}")

        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: urgency_order.get(x["urgency"], 3))

        return jsonify({"data": suggestions})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/forecast", methods=["GET"])
@jwt_required
def get_forecast():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        query    = {"store_id": store_id} if store_id else {}

        items = list(db.inventory.find(query))
        result = []
        for i, item in enumerate(items):
            predicted = item.get("predicted_sales", 0)
            result.append({
                "id":                  str(item["_id"]),
                "product_name":        item.get("product_name", "Unknown"),
                "emoji":               item.get("emoji", "📦"),
                "item_nbr":            str(item.get("sku", i)),
                "predicted_sales":     predicted,
                "base_predicted":      item.get("base_predicted", predicted),
                "forecast_buffer":     item.get("forecast_buffer"),
                "model_predicted_sales": item.get("model_predicted_sales"),
                "baseline_predicted_sales": item.get("baseline_predicted_sales"),
                "prediction_confidence": item.get("prediction_confidence", "low" if predicted else None),
                "seasonal_boost":      item.get("seasonal_boost"),
                "seasonal_multiplier": item.get("seasonal_multiplier", 1.0),
                "stock":               item.get("stock", 0),
                "stock_status":        item.get("stock_status", "Healthy"),
            })

        return jsonify({"data": result})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/ml/run-predictions", methods=["POST"])
@jwt_required
def run_predictions():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId for DB queries
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        sales = list(db.sales.find({"store_id": {"$in": [store_id, store_id_obj]}}))

        records = []
        for sale in sales:
            date_val = sale.get("created_at")
            date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)[:10]

            for item in sale.get("items", []):
                name = item.get("name") or item.get("product_name", "")
                if not name:
                    continue
                records.append({
                    "product_name": name,
                    "qty_sold":     item.get("qty", 1),
                    "date":         date_str,
                    "stockout_limited": bool(item.get("stockout_limited", False)),
                })

            if sale.get("product_name") and not sale.get("items"):
                records.append({
                    "product_name": sale["product_name"],
                    "qty_sold":     sale.get("qty_sold", sale.get("qty", 1)),
                    "date":         date_str,
                })

        if not records:
            return jsonify({"message": "No sales records found", "ready": False}), 200

        unique_dates = sorted({rec["date"] for rec in records})
        if len(unique_dates) < 7:
            return jsonify({
                "message": (
                    f"Not enough sales history yet. Need at least 7 distinct sales days; "
                    f"found {len(unique_dates)}."
                ),
                "ready": False,
                "sales_days": len(unique_dates),
                "sales_records": len(records),
            }), 200

        # Use environment variable for ML path, with fallback to relative path
        ml_path = os.getenv("ML_MODEL_PATH")
        if not ml_path:
            ml_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "inventory-ai", "ml")
            )
        
        if not os.path.exists(ml_path):
            return jsonify({
                "message": f"ML models not found at {ml_path}",
                "ready": False
            }), 500
        
        # Import predict_for_store safely
        if ml_path not in sys.path:
            sys.path.insert(0, ml_path)
        
        try:
            from predict_for_store import predict_for_store
        except ImportError as e:
            return jsonify({
                "message": f"Failed to load ML model: {str(e)}",
                "ready": False
            }), 500

        # 🔧 FIX: Pass product categories for proper family_code mapping
        categories_map = {}
        for rec in records:
            pname = rec["product_name"]
            if pname not in categories_map:
                inv = db.inventory.find_one({
                    "store_id": {"$in": [store_id, store_id_obj]},
                    "product_name": pname
                })
                categories_map[pname] = inv.get("category", "General") if inv else "General"

        predictions = predict_for_store(records, store_id, categories=categories_map)

        # Detect active festivals and custom store events
        from datetime import datetime as dt2, timedelta
        now_dt = dt2.now(timezone.utc)
        import holidays
        ind_holidays = holidays.India(years=now_dt.year)
        active_boosts = {}
        festival_names = []
        
        HOLIDAY_BOOSTS = {
            "diwali": {"categories": ["Sweets","Snacks","Oils","Beverages","Dairy"], "multiplier": 1.5},
            "holi": {"categories": ["Beverages","Dairy","Snacks"], "multiplier": 1.4},
            "christmas": {"categories": ["Bakery","Beverages","Dairy","Eggs"], "multiplier": 1.4},
            "eid": {"categories": ["Grains","Dairy","Oils"], "multiplier": 1.4},
            "new year": {"categories": ["Beverages","Bakery","Snacks"], "multiplier": 1.3},
            "independence day": {"categories": ["Snacks","Beverages"], "multiplier": 1.2},
            "republic day": {"categories": ["Snacks","Beverages"], "multiplier": 1.2},
        }

        # Check today and next 7 days for national holidays
        for i in range(8):
            check_date = (now_dt + timedelta(days=i)).date()
            if check_date in ind_holidays:
                h_name = ind_holidays.get(check_date)
                if h_name not in festival_names:
                    festival_names.append(h_name)
                # Apply boost if defined
                for key, boost_data in HOLIDAY_BOOSTS.items():
                    if key in h_name.lower():
                        for cat in boost_data["categories"]:
                            active_boosts[cat] = max(active_boosts.get(cat, 1.0), boost_data["multiplier"])

        # Apply active store events (promotions, local events)
        in_7_days = now_dt + timedelta(days=7)
        store_events = list(db.store_events.find({
            "store_id": {"$in": [store_id, store_id_obj]},
            "start_date": {"$lte": in_7_days},
            "end_date": {"$gte": now_dt}
        }))
        
        for evt in store_events:
            festival_names.append(evt.get("name", "Store Event"))
            evt_multiplier = evt.get("multiplier", 1.2)
            for cat in evt.get("boost_categories", []):
                active_boosts[cat] = max(active_boosts.get(cat, 1.0), evt_multiplier)

        if festival_names:
            print(f"🎉 Festival boost: {', '.join(festival_names)}")

        now     = datetime.now(timezone.utc)
        updated = 0

        for pred in predictions:
            base_pred = pred["predicted_sales"]

            inv_item = db.inventory.find_one({
                "store_id": {"$in": [store_id, store_id_obj]},
                "product_name": pred["product_name"]
            })
            category = inv_item.get("category", "General") if inv_item else "General"
            stock = float(inv_item.get("stock", 0) or 0) if inv_item else 0
            multiplier = active_boosts.get(category, 1.0)

            # Daily forecast with seasonal/event boost plus a safety buffer.
            # Recent evaluation showed the model under-predicts demand overall,
            # so inventory planning uses a conservative adjusted forecast.
            boosted_pred = base_pred * multiplier
            final_pred = max(round(boosted_pred * FORECAST_UNDERPREDICTION_BUFFER, 2), 0)

            # Guardrail: avoid unrealistic forecasts relative to current stock.
            # 🔧 FIX: Softened from 2× to 5× — the old cap was hiding real demand
            #    and causing chronic under-ordering for fast-moving products.
            if stock > 0:
                final_pred = min(final_pred, round(stock * 5, 2))

            if multiplier > 1.0 or FORECAST_UNDERPREDICTION_BUFFER > 1.0:
                print(f"  🎉 {pred['product_name']} ({category}): {base_pred} → {final_pred} ({multiplier}×)")

            avg_daily = final_pred if final_pred > 0 else max(base_pred, 0)

            # Keep safety stock practical for grocery: roughly one day demand buffer.
            new_safety = max(round(avg_daily), 1)

            # Simplified reorder logic: reorder point ~= predicted daily demand + safety stock.
            new_reorder = max(round(avg_daily + new_safety), new_safety + 1)

            # Extra guardrail: if reorder point is too high vs current stock, soften it.
            if stock > 0 and new_reorder > stock * 2:
                new_reorder = max(round(stock * 1.5), new_safety + 1)

            # ── RECALCULATE STOCK STATUS ──
            # Determine stock status based on stock vs safety/reorder points
            if stock == 0:
                new_status = "Out of Stock"
            elif stock < new_safety:
                new_status = "Low Stock"
            elif stock < new_reorder:
                new_status = "Low Stock"
            else:
                new_status = "Healthy"

            result = db.inventory.update_one(
                {"store_id": {"$in": [store_id, store_id_obj]}, "product_name": pred["product_name"]},
                {"$set": {
                    "predicted_sales":     final_pred,
                    "base_predicted":      base_pred,
                    "forecast_buffer":     FORECAST_UNDERPREDICTION_BUFFER,
                    "model_predicted_sales": pred.get("model_predicted_sales"),
                    "baseline_predicted_sales": pred.get("baseline_predicted_sales"),
                    "prediction_confidence": pred.get("confidence", "low"),
                    "seasonal_boost":      festival_names[0] if festival_names else None,
                    "seasonal_multiplier": multiplier,
                    "safety_stock":        new_safety,
                    "reorder_point":       new_reorder,
                    "stock_status":        new_status,
                    "last_predicted":      now,
                }}
            )
            if result.modified_count:
                updated += 1

            # ── CREATE RESTOCKING ALERTS ──
            # Alert if: High demand predicted BUT stock is insufficient
            if final_pred >= 10 and stock < final_pred * 3:  # Not enough for 3 days of sales
                # Check if alert already exists
                existing_alert = db.alerts.find_one({
                    "product_name": pred["product_name"],
                    "store_id": {"$in": [store_id, store_id_obj]},
                    "status":       "active",
                    "type":         "restock_needed"
                })
                
                if not existing_alert:
                    severity_level = "critical" if stock < final_pred else "warning"
                    alert_msg = f"{pred['product_name']}: Expected {round(final_pred)} units/day but only {round(stock)} in stock — RESTOCK NEEDED!"
                    
                    db.alerts.insert_one({
                        "product_name":     pred["product_name"],
                        "type":             "restock_needed",
                        "message":          alert_msg,
                        "severity":         severity_level,
                        "status":           "active",
                        "store_id":         store_id,
                        "predicted_demand": final_pred,
                        "current_stock":    stock,
                        "created_at":       now,
                    })
                    print(f"  🚨 Alert created: {alert_msg}")

        festival_msg = (
            f" (🎉 {', '.join(festival_names)} boost applied!)"
            if festival_names else ""
        )

        return jsonify({
            "message":     f"✅ Predictions updated for {updated} products{festival_msg}",
            "predictions": predictions,
            "festivals":   festival_names,
            "ready":       True,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/reorder/orders", methods=["GET"])
@jwt_required
def get_reorder_orders():
    """Get all reorder orders (pending, approved, dismissed) for this store."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id
        
        status_filter = request.args.get("status", "")  # pending | approved | dismissed | all
        query = {"store_id": {"$in": [store_id, store_id_obj]}}
        
        if status_filter and status_filter != "all":
            query["status"] = status_filter
        
        orders = list(db.reorder_orders.find(query).sort("created_at", -1))
        
        result = []
        for order in orders:
            order["id"] = str(order.pop("_id"))
            if "created_at" in order:
                order["created_at"] = order["created_at"].isoformat()
            if "approved_at" in order and order["approved_at"]:
                order["approved_at"] = order["approved_at"].isoformat()
            if "dismissed_at" in order and order["dismissed_at"]:
                order["dismissed_at"] = order["dismissed_at"].isoformat()
            result.append(order)
        
        # Calculate total cost for pending orders
        total_pending_cost = sum(o.get("est_cost", 0) for o in result if o.get("status") == "pending")
        
        return jsonify({
            "data": result,
            "total_pending_cost": total_pending_cost,
            "total_orders": len(result)
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Reorder Approve / Dismiss ─────────────────────────────────────────

@ml_bp.route("/reorder/<item_id>/approve", methods=["POST"])
@jwt_required
def approve_reorder(item_id):
    """Mark a reorder suggestion as approved."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        now      = datetime.now(timezone.utc)
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        result = db.reorder_orders.update_one(
            {"_id": ObjectId(item_id), "store_id": {"$in": [store_id, store_id_obj]}},
            {"$set": {
                "status": "approved", 
                "approved_at": now, 
                "approved_by": request.current_user.get("sub")
            }}
        )
        
        if not result.matched_count:
            return jsonify({"message": "Reorder not found or unauthorized"}), 404
        
        return jsonify({"message": "Reorder approved"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/reorder/<item_id>/dismiss", methods=["POST"])
@jwt_required
def dismiss_reorder(item_id):
    """Dismiss a reorder suggestion."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        now      = datetime.now(timezone.utc)
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        result = db.reorder_orders.update_one(
            {"_id": ObjectId(item_id), "store_id": {"$in": [store_id, store_id_obj]}},
            {"$set": {
                "status": "dismissed", 
                "dismissed_at": now,
                "dismissed_by": request.current_user.get("sub")
            }}
        )
        
        if not result.matched_count:
            return jsonify({"message": "Reorder not found or unauthorized"}), 404
        
        return jsonify({"message": "Reorder dismissed"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/reorder/<item_id>/delivered", methods=["POST"])
@jwt_required
def mark_reorder_delivered(item_id):
    """Mark a reorder as delivered and received into inventory (atomic transaction)."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        data     = request.get_json()
        
        # ✅ VALIDATE DELIVERY DATA
        success, result = validate_request(ReorderDeliverySchema, data)
        if not success:
            return jsonify(result), 400
        
        validated_data = result
        
        # ✅ EXECUTE ATOMIC TRANSACTION
        tx_manager = TransactionManager(db.client, db)
        success, tx_result, error = tx_manager.execute_transaction(
            transaction_reorder_delivery,
            db=db,
            order_id=item_id,
            received_qty=validated_data["received_qty"]
        )
        
        if not success:
            return jsonify({"error": error}), 500
        
        return jsonify({
            "message": f"Reorder marked delivered (+{tx_result['order'].get('delivered_qty', 0)} units)",
            "order": {
                "id": str(tx_result["order"]["_id"]),
                "status": tx_result["order"]["status"],
                "delivered_at": tx_result["order"].get("delivered_at", "").isoformat() if tx_result["order"].get("delivered_at") else None,
                "stock_after": tx_result["inventory"].get("stock", 0)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Reorder Settings ──────────────────────────────────────────────────

@ml_bp.route("/reorder/settings", methods=["GET"])
@jwt_required
def get_reorder_settings():
    """Get reorder configuration for this store."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        settings = db.reorder_settings.find_one({"store_id": store_id_obj})
        if not settings:
            # Return defaults
            settings = {
                "store_id":          store_id_obj,
                "default_restock_days": 7,
                "safety_multiplier":   1.5,
                "auto_approve":        False,
                "min_order_value":     500,
            }
            db.reorder_settings.insert_one(settings)
            settings.pop("_id", None)
        else:
            settings["id"] = str(settings.pop("_id"))

        return jsonify(settings)
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/reorder/settings", methods=["PUT"])
@jwt_required
def update_reorder_settings():
    """Update reorder configuration."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        data     = request.get_json()
        now      = datetime.now(timezone.utc)
        
        # ✅ VALIDATE REORDER SETTINGS
        success, result = validate_request(ReorderSettingsSchema, data)
        if not success:
            return jsonify(result), 400
        
        validated_data = result
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        db.reorder_settings.update_one(
            {"store_id": store_id_obj},
            {"$set": {
                "default_restock_days": validated_data["default_restock_days"],
                "safety_multiplier":    validated_data["safety_multiplier"],
                "auto_approve":         validated_data["auto_approve"],
                "min_order_value":      validated_data["min_order_value"],
                "updated_at":           now,
            }},
            upsert=True
        )
        return jsonify({"message": "Reorder settings updated"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Forecast Accuracy ─────────────────────────────────────────────────

@ml_bp.route("/forecast/accuracy", methods=["GET"])
@jwt_required
def get_forecast_accuracy():
    """Compare past predictions vs actual sales."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id
        
        query    = {"store_id": store_id_obj} if store_id else {}

        # Get inventory items with predictions
        items = list(db.inventory.find({**query, "predicted_sales": {"$gt": 0}}))

        accuracy_data = []
        for item in items:
            predicted = item.get("predicted_sales", 0)
            if predicted == 0:
                continue

            # Sum actual sales for this product in last 7 days
            from datetime import timedelta
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)

            pipeline = [
                {"$match": {
                    "store_id": store_id_obj,
                    "created_at": {"$gte": week_ago},
                }},
                {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": True}},
                {"$match": {
                    "$or": [
                        {"items.name": item.get("product_name")},
                        {"product_name": item.get("product_name")},
                    ]
                }},
                {"$group": {
                    "_id": None,
                    "actual_total": {"$sum": {"$ifNull": ["$items.qty", "$subtotal"]}},
                    "days": {"$addToSet": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}},
                }},
            ]

            result = list(db.sales.aggregate(pipeline))
            actual = result[0]["actual_total"] if result else 0
            days   = len(result[0]["days"]) if result else 0
            daily_actual = actual / max(days, 1)

            error_pct = abs(predicted - daily_actual) / max(predicted, 1) * 100
            accuracy  = max(0, 100 - error_pct)

            accuracy_data.append({
                "product_name":    item.get("product_name", "Unknown"),
                "emoji":           item.get("emoji", "📦"),
                "predicted_daily": round(predicted, 2),
                "actual_daily":    round(daily_actual, 2),
                "accuracy_pct":    round(accuracy, 1),
                "days_of_data":    days,
            })

        accuracy_data.sort(key=lambda x: x["accuracy_pct"], reverse=True)
        avg_accuracy = round(
            sum(a["accuracy_pct"] for a in accuracy_data) / max(len(accuracy_data), 1), 1
        )

        return jsonify({
            "data":            accuracy_data,
            "avg_accuracy":    avg_accuracy,
            "products_tracked": len(accuracy_data),
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ml_bp.route("/forecast/comparison", methods=["GET"])
@jwt_required
def get_forecast_comparison():
    """Predicted vs Actual comparison per product."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id
        
        query    = {"store_id": store_id_obj} if store_id else {}

        items = list(db.inventory.find(query))
        comparison = []

        from datetime import timedelta
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        for item in items:
            predicted = item.get("predicted_sales", 0)

            pipeline = [
                {"$match": {
                    "store_id": store_id_obj,
                    "created_at": {"$gte": week_ago},
                }},
                {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": True}},
                {"$match": {
                    "$or": [
                        {"items.name": item.get("product_name")},
                        {"product_name": item.get("product_name")},
                    ]
                }},
                {"$group": {
                    "_id": None,
                    "actual": {"$sum": {"$ifNull": ["$items.qty", 1]}},
                }},
            ]

            result = list(db.sales.aggregate(pipeline))
            actual = result[0]["actual"] if result else 0

            comparison.append({
                "product_name": item.get("product_name", "Unknown"),
                "emoji":        item.get("emoji", "📦"),
                "predicted":    round(predicted, 2),
                "actual":       round(actual, 2),
                "difference":   round(predicted - actual, 2),
                "status":       "over" if predicted > actual else "under" if predicted < actual else "accurate",
            })

        return jsonify({"data": comparison})
    except Exception as e:
        return jsonify({"message": str(e)}), 500
