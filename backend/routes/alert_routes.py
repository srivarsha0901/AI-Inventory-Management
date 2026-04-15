from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone

alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/alerts", methods=["GET"])
@jwt_required
def get_alerts():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        try:
            store_id_obj = ObjectId(store_id) if store_id else None
        except:
            store_id_obj = store_id

        store_ids = [store_id] if store_id else []
        if store_id_obj and store_id_obj != store_id:
            store_ids.append(store_id_obj)

        query = {"status": "active"}
        if store_ids:
            query["store_id"] = {"$in": store_ids}

        # Backfill missing low-stock alerts from inventory using reorder point.
        inventory_query = {"store_id": {"$in": store_ids}} if store_ids else {}
        inventory_items = list(db.inventory.find(inventory_query))
        now = datetime.now(timezone.utc)
        for item in inventory_items:
            stock = int(item.get("stock", 0) or 0)
            reorder_point = int(item.get("reorder_point", item.get("safety_stock", 10)) or 0)
            if stock > reorder_point:
                continue

            product_name = item.get("product_name") or item.get("name") or "Unknown product"
            existing = db.alerts.find_one({
                "product_name": product_name,
                "status": "active",
                "store_id": {"$in": store_ids} if store_ids else item.get("store_id"),
                "type": "low_stock",
            })
            if existing:
                continue

            db.alerts.insert_one({
                "product_name": product_name,
                "type": "low_stock",
                "message": f"{stock} {item.get('unit', 'units')} left — below reorder point of {reorder_point}",
                "severity": "critical" if stock == 0 else "warning",
                "status": "active",
                "store_id": item.get("store_id", store_id),
                "created_at": now,
            })

        alerts = list(db.alerts.find(query).sort("created_at", -1))
        for a in alerts:
            a["id"] = str(a.pop("_id"))
            if "created_at" in a:
                a["created_at"] = a["created_at"].isoformat()
        return jsonify({"data": alerts})
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@alerts_bp.route("/alerts/<alert_id>/dismiss", methods=["POST"])
@jwt_required
def dismiss_alert(alert_id):
    try:
        db = get_db()
        db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {"status": "dismissed", "updated_at": datetime.now(timezone.utc)}}
        )
        return jsonify({"message": "Alert dismissed"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@alerts_bp.route("/alerts/<alert_id>/resolve", methods=["POST"])
@jwt_required
def resolve_alert(alert_id):
    try:
        db = get_db()
        db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {"status": "resolved", "updated_at": datetime.now(timezone.utc)}}
        )
        return jsonify({"message": "Alert resolved"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@alerts_bp.route("/alerts/dismiss-all", methods=["PATCH"])
@jwt_required
def dismiss_all_alerts():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        query    = {"status": "active"}
        if store_id:
            query["store_id"] = store_id

        result = db.alerts.update_many(
            query,
            {"$set": {"status": "dismissed", "updated_at": datetime.now(timezone.utc)}}
        )
        return jsonify({"message": f"{result.modified_count} alerts dismissed"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500