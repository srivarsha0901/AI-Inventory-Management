from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from database import get_db


class User:
    COLLECTION = "users"
    ROLES      = ("manager", "cashier", "admin")

    @classmethod
    def _col(cls):
        return get_db()[cls.COLLECTION]

    # ── Finders ──────────────────────────────────────────────────────────────

    @classmethod
    def find_by_email(cls, email):
        return cls._col().find_one({"email": email.lower().strip()})

    @classmethod
    def find_by_id(cls, user_id):
        try:
            return cls._col().find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    @classmethod
    def find_all(cls):
        return list(cls._col().find({}, {"password_hash": 0}))

    # ── Create ────────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, name, email, password, role="cashier"):
        if role not in cls.ROLES:
            raise ValueError(f"Invalid role '{role}'")

        now = datetime.now(timezone.utc)
        doc = {
            "name":          name.strip(),
            "email":         email.lower().strip(),
            "password_hash": generate_password_hash(password),
            "role":          role,
            "is_active":     True,
            "created_at":    now,
            "updated_at":    now,
            "last_login":    None,
        }
        result = cls._col().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    # ── Update ────────────────────────────────────────────────────────────────

    @classmethod
    def update_last_login(cls, user_id):
        cls._col().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )

    # ── Auth ──────────────────────────────────────────────────────────────────

    @staticmethod
    def verify_password(user_doc, password):
        return check_password_hash(user_doc["password_hash"], password)

    # ── Serialise ─────────────────────────────────────────────────────────────

    @staticmethod
    def to_public(user_doc):
        return {
            "id":         str(user_doc["_id"]),
            "name":       user_doc.get("name", ""),
            "email":      user_doc.get("email", ""),
            "role":       user_doc.get("role", ""),
            "is_active":  user_doc.get("is_active", True),
            "last_login": user_doc.get("last_login"),
            "created_at": user_doc.get("created_at"),
        }