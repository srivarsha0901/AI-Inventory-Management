import jwt
from datetime import datetime, timezone
from functools import wraps
from flask import request, jsonify, current_app


def generate_token(user_doc):
    now     = datetime.now(timezone.utc)
    expires = now + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]

    payload = {
    "sub":      str(user_doc["_id"]),
    "email":    user_doc["email"],
    "role":     user_doc["role"],
    "name":     user_doc.get("name", ""),
    "store_id": str(user_doc.get("store_id", "")),
    "iat":      now,
    "exp":      expires,
}


    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def decode_token(token):
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=[current_app.config["JWT_ALGORITHM"]],
    )


def _extract_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


# ── Decorators ────────────────────────────────────────────────────────────────

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()

        if not token:
            return jsonify({"message": "Authorization token missing"}), 401

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired. Please log in again."}), 401
        except jwt.InvalidTokenError as exc:
            return jsonify({"message": f"Invalid token: {exc}"}), 401

        request.current_user = payload
        return f(*args, **kwargs)

    return decorated


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated(*args, **kwargs):
            if request.current_user.get("role") not in allowed_roles:
                return jsonify({"message": f"Access denied. Requires: {', '.join(allowed_roles)}"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
