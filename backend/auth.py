from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from database import get_db
from jwt_helper import generate_token, jwt_required
from bson import ObjectId
from validation import RegisterSchema, validate_request

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    db   = get_db()
    data = request.get_json()

    # ✅ VALIDATE REGISTRATION DATA
    success, result = validate_request(RegisterSchema, data)
    if not success:
        return jsonify(result), 400
    
    validated_data = result

    if db.users.find_one({"email": validated_data["email"]}):
        return jsonify({"message": "Email already registered"}), 409

    now      = datetime.now(timezone.utc)
    store_id = db.stores.insert_one({
        "name":       validated_data["store_name"],
        "address":    validated_data["address"],
        "created_at": now,
        "is_active":  True,
    }).inserted_id

    user = {
        "name":                validated_data["name"],
        "email":               validated_data["email"],
        "password_hash":       generate_password_hash(validated_data["password"]),
        "role":                "manager",
        "store_id":            store_id,
        "is_active":           True,
        "created_at":          now,
        "last_login":          None,
        "onboarding_complete": False,
    }
    user["_id"] = db.users.insert_one(user).inserted_id

    return jsonify({
        "message": "Registration successful",
        "token":   generate_token(user),
        "user": {
            "id":                  str(user["_id"]),
            "name":                validated_data["name"],
            "email":               validated_data["email"],
            "role":                "manager",
            "store_id":            str(store_id),
            "onboarding_complete": False,
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    db   = get_db()
    data = request.get_json()

    user = db.users.find_one({"email": {"$regex": f"^{data.get('email', '')}$", "$options": "i"}})
    if not user or not check_password_hash(user["password_hash"], data.get("password", "")):
        return jsonify({"message": "Invalid email or password"}), 401

    db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})

    return jsonify({
        "token": generate_token(user),
        "user": {
            "id":                  str(user["_id"]),
            "name":                user["name"],
            "email":               user["email"],
            "role":                user["role"],
            "store_id":            str(user.get("store_id", "")),
            "onboarding_complete": user.get("onboarding_complete", True),
        }
    })


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required
def refresh():
    """Refresh JWT token (called 1 hour before expiry)."""
    try:
        user = request.current_user
        db = get_db()
        
        # Get full user document (to ensure we have latest data)
        user_doc = db.users.find_one({"_id": ObjectId(user.get("sub"))})
        if not user_doc or not user_doc.get("is_active"):
            return jsonify({"message": "User not found or inactive"}), 401
        
        # Generate new token
        new_token = generate_token(user_doc)
        
        return jsonify({
            "token": new_token,
            "user": {
                "id":                  str(user_doc["_id"]),
                "name":                user_doc["name"],
                "email":               user_doc["email"],
                "role":                user_doc["role"],
                "store_id":            str(user_doc.get("store_id", "")),
                "onboarding_complete": user_doc.get("onboarding_complete", True),
            }
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@auth_bp.route("/create-cashier", methods=["POST"])
@jwt_required
def create_cashier():
    db       = get_db()
    data     = request.get_json()
    store_id = request.current_user.get("store_id")

    if request.current_user.get("role") != "manager":
        return jsonify({"message": "Only managers can create cashier accounts"}), 403

    if db.users.find_one({"email": data.get("email", "")}):
        return jsonify({"message": "Email already exists"}), 409

    now     = datetime.now(timezone.utc)
    # Convert store_id from JWT string back to ObjectId for DB storage
    try:
        store_id_obj = ObjectId(store_id) if store_id else None
    except:
        store_id_obj = None
    
    cashier = {
        "name":                data["name"],
        "email":               data["email"],
        "password_hash":       generate_password_hash(data["password"]),
        "role":                "cashier",
        "store_id":            store_id_obj,
        "is_active":           True,
        "created_at":          now,
        "last_login":          None,
        "onboarding_complete": True,
    }
    cashier_id = db.users.insert_one(cashier).inserted_id

    return jsonify({
        "message": "Cashier created successfully",
        "cashier": {
            "id":    str(cashier_id),
            "name":  data["name"],
            "email": data["email"],
            "role":  "cashier",
        }
    }), 201


@auth_bp.route("/onboarding-complete", methods=["POST"])
@jwt_required
def onboarding_complete():
    db      = get_db()
    user_id = request.current_user.get("sub")
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"onboarding_complete": True}}
    )
    return jsonify({"message": "Onboarding complete"})


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_me():
    db      = get_db()
    user_id = request.current_user.get("sub")
    user    = db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify({
        "user": {
            "id":                  str(user["_id"]),
            "name":                user.get("name", ""),
            "email":               user.get("email", ""),
            "role":                user.get("role", ""),
            "store_id":            str(user.get("store_id", "")),
            "onboarding_complete": user.get("onboarding_complete", True),
        }
    })


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    # JWT is stateless — client should discard token.
    # This endpoint exists for frontend compatibility.
    return jsonify({"message": "Logged out successfully"})