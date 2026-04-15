from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
from validation import StaffSchema, validate_request

staff_bp = Blueprint("staff", __name__)

# ── Create salesman ───────────────────────────────────────
@staff_bp.route("/staff", methods=["POST"])
@jwt_required
def create_staff():
    try:
        db       = get_db()
        user     = request.current_user
        store_id = user.get("store_id")

        if user.get("role") != "manager":
            return jsonify({"message": "Only managers can create staff"}), 403

        data = request.get_json()
        
        # ✅ VALIDATE STAFF DATA
        success, result = validate_request(StaffSchema, data)
        if not success:
            return jsonify(result), 400
        
        validated_data = result

        if db.users.find_one({"email": validated_data["email"]}):
            return jsonify({"message": "Email already exists"}), 409

        now     = datetime.now(timezone.utc)
        cashier = {
            "name":                validated_data["name"],
            "email":               validated_data["email"],
            "password_hash":       generate_password_hash(validated_data["password"]),
            "role":                "cashier",
            "store_id":            ObjectId(store_id) if store_id else None,
            "is_active":           True,
            "created_at":          now,
            "last_login":          None,
            "onboarding_complete": True,
        }
        cashier_id = db.users.insert_one(cashier).inserted_id

        # Log activity
        _log(db, store_id, user.get("sub"), user.get("name"),
             "staff_created", f"Created salesman account: {validated_data['name']} ({validated_data['email']})")

        return jsonify({
            "message": "Salesman created",
            "staff": {
                "id":    str(cashier_id),
                "name":  validated_data["name"],
                "email": validated_data["email"],
                "role":  "cashier",
            }
        }), 201

    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Get all staff for this store ──────────────────────────
@staff_bp.route("/staff", methods=["GET"])
@jwt_required
def get_staff():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id from string to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        staff = list(db.users.find(
            {"store_id": store_id_obj, "role": "cashier"},
            {"password_hash": 0}
        ))
        for s in staff:
            s["id"] = str(s.pop("_id"))
            s["store_id"] = str(s.get("store_id",""))
            if s.get("created_at"):
                s["created_at"] = s["created_at"].isoformat()
            if s.get("last_login"):
                s["last_login"] = s["last_login"].isoformat()

            # Get their sales count
            s["total_sales"] = db.sales.count_documents({
                "store_id":   store_id,
                "cashier_id": s["id"],
            })

        return jsonify({"data": staff})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Deactivate staff ──────────────────────────────────────
@staff_bp.route("/staff/<staff_id>/deactivate", methods=["POST"])
@jwt_required
def deactivate_staff(staff_id):
    try:
        db   = get_db()
        user = request.current_user
        if user.get("role") != "manager":
            return jsonify({"message": "Only managers can deactivate staff"}), 403

        db.users.update_one(
            {"_id": ObjectId(staff_id)},
            {"$set": {"is_active": False}}
        )
        _log(db, user.get("store_id"), user.get("sub"), user.get("name"),
             "staff_deactivated", f"Deactivated staff ID: {staff_id}")

        return jsonify({"message": "Staff deactivated"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Activity log ──────────────────────────────────────────
@staff_bp.route("/activity", methods=["GET"])
@jwt_required
def get_activity():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")

        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        skip     = (page - 1) * per_page

        staff_id = request.args.get("staff_id")  # filter by specific staff
        query    = {"store_id": store_id}
        if staff_id:
            query["user_id"] = staff_id

        total  = db.activity_log.count_documents(query)
        logs   = list(db.activity_log.find(query).sort("created_at", -1).skip(skip).limit(per_page))
        for l in logs:
            l["id"] = str(l.pop("_id"))
            if "created_at" in l:
                l["created_at"] = l["created_at"].isoformat()

        return jsonify({"data": logs, "total": total})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Sales by staff ────────────────────────────────────────
@staff_bp.route("/staff/<staff_id>/sales", methods=["GET"])
@jwt_required
def get_staff_sales(staff_id):
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")

        sales = list(db.sales.find(
            {"store_id": store_id, "cashier_id": staff_id}
        ).sort("created_at", -1).limit(50))

        for s in sales:
            s["id"] = str(s.pop("_id"))
            if "created_at" in s:
                s["created_at"] = s["created_at"].isoformat()

        return jsonify({"data": sales})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Helper ────────────────────────────────────────────────
def _log(db, store_id, user_id, user_name, action, detail):
    """Log activity to audit trail. Handles both string and ObjectId types."""
    try:
        # Convert store_id from string to ObjectId if needed
        if isinstance(store_id, str) and store_id:
            try:
                store_id_obj = ObjectId(store_id)
            except:
                store_id_obj = store_id  # Keep as string if conversion fails
        else:
            store_id_obj = store_id
        
        # Convert user_id from string to ObjectId if needed
        if isinstance(user_id, str) and user_id:
            try:
                user_id_obj = ObjectId(user_id)
            except:
                user_id_obj = user_id
        else:
            user_id_obj = user_id
        
        db.activity_log.insert_one({
            "store_id":   store_id_obj,
            "user_id":    user_id_obj,
            "user_name":  user_name,
            "action":     action,
            "detail":     detail,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception as e:
        # Don't crash main flow if logging fails
        print(f"⚠️ Activity log error: {str(e)}")