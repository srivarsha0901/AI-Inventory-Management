from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
from routes.staff_routes import _log
from validation import SaleSchema, validate_request
from transactions import TransactionManager, transaction_complete_sale
from caching import get_cache
pos_bp = Blueprint("pos", __name__)

@pos_bp.route("/products", methods=["GET"])
@jwt_required
def get_products():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Security: must have store_id or return 401
        if not store_id:
            return jsonify({"message": "Store ID missing from token"}), 401
        
        # Convert store_id from string to ObjectId if needed
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id
        
        store_ids = [store_id]
        if store_id_obj != store_id:
            store_ids.append(store_id_obj)

        # Treat missing `is_active` as active for onboarding-imported products.
        query = {
            "store_id": {"$in": store_ids},
            "$or": [
                {"is_active": True},
                {"is_active": {"$exists": False}}
            ]
        }

        q = request.args.get("q", "")
        if q:
            query["name"] = {"$regex": q, "$options": "i"}

        products = list(db.products.find(query))
        result   = []
        for p in products:
            inv = db.inventory.find_one({"product_id": p["_id"]})
            result.append({
                "id":       str(p["_id"]),
                "name":     p["name"],
                "emoji":    p.get("emoji", "📦"),
                "price": p.get("selling_price", 0),
                "unit":     p.get("unit", "units"),
                "category": p.get("category", "General").lower(),
                "stock":    inv.get("stock", 0) if inv else 0,
            })
        return jsonify({"data": result})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@pos_bp.route("/sales", methods=["POST"])
@jwt_required
def create_sale():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        user_id  = request.current_user.get("sub")
        data     = request.get_json()
        now      = datetime.now(timezone.utc)

        # ✅ VALIDATE SALE DATA
        success, result = validate_request(SaleSchema, data)
        if not success:
            return jsonify(result), 400
        
        validated_data = result

        # ✅ EXECUTE ATOMIC TRANSACTION (Sale + Inventory + Alerts)
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id
        
        sale_data_to_process = {
            "store_id": store_id_obj,
            "items": validated_data["items"],
            "subtotal": validated_data["subtotal"],
            "tax": validated_data["tax"],
            "total": validated_data["total"],
        }
        
        tx_manager = TransactionManager(db.client, db)
        success, tx_result, error = tx_manager.execute_transaction(
            transaction_complete_sale,
            db=db,
            sale_data=sale_data_to_process
        )
        
        if not success:
            return jsonify({"error": error}), 500
        
        # Log the sale (after successful transaction)
        _log(db, store_id, user_id,
             request.current_user.get("name", "Cashier"),
             "sale_created",
             f"Sale of ₹{validated_data['total']} — {len(validated_data['items'])} items")

        # ✅ INVALIDATE CACHE (Dashboard stats need update)
        cache = get_cache()
        cache.delete(f"dashboard_stats:{store_id}")

        return jsonify({
            "message": "Sale recorded successfully (atomic transaction)",
            "sale_id": tx_result["sale_id"],
            "total": tx_result["total"]
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@pos_bp.route("/sales", methods=["GET"])
@jwt_required
def get_sales():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        if store_id:
            try:
                store_id_obj = ObjectId(store_id)
            except:
                store_id_obj = store_id

            store_ids = [store_id]
            if store_id_obj != store_id:
                store_ids.append(store_id_obj)
            query = {"store_id": {"$in": store_ids}}
        else:
            query = {}

        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        skip     = (page - 1) * per_page

        total = db.sales.count_documents(query)
        sales = list(db.sales.find(query).sort("created_at", -1).skip(skip).limit(per_page))
        for s in sales:
            s["id"] = str(s.pop("_id"))
            if "created_at" in s:
                s["created_at"] = s["created_at"].isoformat()
        return jsonify({"data": sales, "total": total})
    except Exception as e:
        return jsonify({"message": str(e)}), 500