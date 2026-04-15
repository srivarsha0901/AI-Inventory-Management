from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
from caching import get_cache

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard/stats", methods=["GET"])
@jwt_required
def get_stats():
    """Get dashboard stats (cached for 5 minutes)."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # ✅ CHECK CACHE FIRST
        cache = get_cache()
        cache_key = f"dashboard_stats:{store_id}"
        cached_stats = cache.get(cache_key)
        if cached_stats:
            return jsonify(cached_stats)
        
        query    = {"store_id": store_id} if store_id else {}

        total_products   = db.inventory.count_documents(query)
        low_stock_count  = db.inventory.count_documents({
            **query,
            "stock_status": {"$in": ["Low Stock", "Out of Stock"]}
        })
        total_forecasted = sum(
            d.get("predicted_sales", 0)
            for d in db.inventory.find(query, {"predicted_sales": 1})
        )

        today_start   = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        revenue_today = sum(
            s.get("total", 0)
            for s in db.sales.find({**query, "created_at": {"$gte": today_start}})
        )
        total_sales = db.sales.count_documents(query)

        stats = {
            "total_products":   total_products,
            "low_stock_count":  low_stock_count,
            "total_forecasted": int(total_forecasted),
            "revenue_today":    revenue_today,
            "total_sales":      total_sales,
        }
        
        # ✅ CACHE FOR 5 MINUTES
        cache.set(cache_key, stats, ttl_minutes=5)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/dashboard/alerts", methods=["GET"])
@jwt_required
def get_alerts():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        query    = {"status": "active"}
        if store_id:
            query["store_id"] = store_id

        alerts = list(db.alerts.find(query).sort("created_at", -1).limit(10))
        for a in alerts:
            a["id"] = str(a.pop("_id"))
        return jsonify({"data": alerts})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/dashboard/sales-trend", methods=["GET"])
@jwt_required
def get_sales_trend():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        period   = request.args.get("period", "week")
        limit    = 7 if period == "week" else 30
        query    = {"store_id": store_id} if store_id else {}

        sales = list(db.sales.find(query).sort("created_at", -1).limit(limit))
        for s in sales:
            s["id"] = str(s.pop("_id"))
            if "created_at" in s:
                s["created_at"] = s["created_at"].isoformat()
        return jsonify({"data": sales, "period": period})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/inventory", methods=["GET"])
@jwt_required
def get_inventory():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        query    = {"store_id": store_id} if store_id else {}

        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        skip     = (page - 1) * per_page

        total   = db.inventory.count_documents(query)
        records = list(db.inventory.find(query).skip(skip).limit(per_page))
        for r in records:
            r["id"]         = str(r.pop("_id"))
            r["product_id"] = str(r.get("product_id", ""))
        return jsonify({
            "data":     records,
            "total":    total,
            "page":     page,
            "per_page": per_page,
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/inventory/<item_id>", methods=["PUT"])
@jwt_required
def update_inventory(item_id):
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        data     = request.get_json()
        now      = datetime.now(timezone.utc)

        stock         = int(data.get("stock", 0))
        safety        = int(data.get("safety_stock", 10))
        reorder_point = int(data.get("reorder_point", safety + 5))

        status = (
            "Out of Stock" if stock == 0 else
            "Low Stock" if stock <= reorder_point else
            "Healthy"
        )

        db.inventory.update_one(
            {"_id": ObjectId(item_id), "store_id": store_id},
            {"$set": {
                "stock":         stock,
                "reorder_point": reorder_point,
                "stock_status":  status,
                "last_updated":  now,
            }}
        )

        # Auto-create alert if now low stock
        if status in ("Low Stock", "Out of Stock"):
            item = db.inventory.find_one({"_id": ObjectId(item_id)})
            if item:
                existing = db.alerts.find_one({
                    "product_name": item.get("product_name"),
                    "store_id":     store_id,
                    "status":       "active",
                })
                if not existing:
                    db.alerts.insert_one({
                        "product_name": item.get("product_name", "Unknown"),
                        "type":         "low_stock",
                        "message":      f"{stock} {item.get('unit','units')} left — below reorder point of {reorder_point}",
                        "severity":     "critical" if status == "Out of Stock" else "warning",
                        "status":       "active",
                        "store_id":     store_id,
                        "created_at":   now,
                    })

        return jsonify({"message": "Inventory updated"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/inventory/<item_id>", methods=["DELETE"])
@jwt_required
def delete_inventory(item_id):
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")

        item = db.inventory.find_one({"_id": ObjectId(item_id), "store_id": store_id})
        if not item:
            return jsonify({"message": "Item not found"}), 404

        db.inventory.delete_one({"_id": ObjectId(item_id)})

        if item.get("product_id"):
            db.products.delete_one({"_id": item["product_id"]})

        db.alerts.update_many(
            {"product_name": item.get("product_name"), "store_id": store_id},
            {"$set": {"status": "dismissed"}}
        )

        return jsonify({"message": "Product removed"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/dashboard/top-products", methods=["GET"])
@jwt_required
def get_top_products():
    """Top selling products by revenue."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        query    = {"store_id": store_id} if store_id else {}

        pipeline = [
            {"$match": query},
            {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": {"$ifNull": ["$items.name", "$product_name"]},
                "total_qty":     {"$sum": {"$ifNull": ["$items.qty", "$subtotal"]}},
                "total_revenue": {"$sum": {"$ifNull": ["$total", 0]}},
                "sale_count":    {"$sum": 1},
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": 10},
        ]

        results = list(db.sales.aggregate(pipeline))
        data = []
        for r in results:
            if not r["_id"]:
                continue
            data.append({
                "product_name":  r["_id"],
                "total_qty":     round(r.get("total_qty", 0), 1),
                "total_revenue": round(r.get("total_revenue", 0), 2),
                "sale_count":    r.get("sale_count", 0),
            })

        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/inventory/low-stock", methods=["GET"])
@jwt_required
def get_low_stock():
    """Get all low stock / out of stock items."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        query    = {"store_id": store_id} if store_id else {}
        query["stock_status"] = {"$in": ["Low Stock", "Out of Stock"]}

        records = list(db.inventory.find(query).sort("stock", 1))
        for r in records:
            r["id"]         = str(r.pop("_id"))
            r["product_id"] = str(r.get("product_id", ""))
        return jsonify({"data": records})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@dashboard_bp.route("/inventory/expiring", methods=["GET"])
@jwt_required
def get_expiring():
    """Get items approaching expiry (if expiry_date field exists)."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        now      = datetime.now(timezone.utc)

        from datetime import timedelta
        threshold = now + timedelta(days=7)

        query = {"store_id": store_id} if store_id else {}
        query["expiry_date"] = {"$lte": threshold, "$gte": now}

        records = list(db.inventory.find(query).sort("expiry_date", 1))
        for r in records:
            r["id"]         = str(r.pop("_id"))
            r["product_id"] = str(r.get("product_id", ""))
            if "expiry_date" in r:
                r["expiry_date"] = r["expiry_date"].isoformat()
        return jsonify({"data": records})
    except Exception as e:
        return jsonify({"message": str(e)}), 500