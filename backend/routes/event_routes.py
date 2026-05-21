from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
import dateutil.parser

events_bp = Blueprint("events", __name__)

@events_bp.route("/events", methods=["GET"])
@jwt_required
def get_events():
    """Get all events for the current store."""
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        
        # Convert store_id to ObjectId
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        events = list(db.store_events.find({"store_id": {"$in": [store_id, store_id_obj]}}))
        
        result = []
        for event in events:
            event["id"] = str(event.pop("_id"))
            if "start_date" in event and event["start_date"]:
                event["start_date"] = event["start_date"].isoformat()
            if "end_date" in event and event["end_date"]:
                event["end_date"] = event["end_date"].isoformat()
            # Default to store_id string format for frontend consistency
            if "store_id" in event:
                event["store_id"] = str(event["store_id"])
            result.append(event)
            
        return jsonify({"data": result})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@events_bp.route("/events", methods=["POST"])
@jwt_required
def create_event():
    """Create a new event."""
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        data = request.get_json()
        
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        # Parse dates
        start_date = dateutil.parser.parse(data.get("start_date")) if data.get("start_date") else datetime.now(timezone.utc)
        end_date = dateutil.parser.parse(data.get("end_date")) if data.get("end_date") else start_date

        event = {
            "store_id": store_id_obj,
            "name": data.get("name"),
            "event_type": data.get("event_type", "promotion"), # promotion, local_event, holiday
            "start_date": start_date,
            "end_date": end_date,
            "boost_categories": data.get("boost_categories", []),
            "multiplier": float(data.get("multiplier", 1.2)),
            "created_at": datetime.now(timezone.utc),
            "created_by": request.current_user.get("sub")
        }

        result = db.store_events.insert_one(event)
        event["id"] = str(result.inserted_id)
        event.pop("_id", None)
        
        return jsonify({"message": "Event created", "data": event}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@events_bp.route("/events/<event_id>", methods=["PUT"])
@jwt_required
def update_event(event_id):
    """Update an existing event."""
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        data = request.get_json()
        
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        update_fields = {}
        if "name" in data: update_fields["name"] = data["name"]
        if "event_type" in data: update_fields["event_type"] = data["event_type"]
        if "start_date" in data: update_fields["start_date"] = dateutil.parser.parse(data["start_date"])
        if "end_date" in data: update_fields["end_date"] = dateutil.parser.parse(data["end_date"])
        if "boost_categories" in data: update_fields["boost_categories"] = data["boost_categories"]
        if "multiplier" in data: update_fields["multiplier"] = float(data["multiplier"])

        result = db.store_events.update_one(
            {"_id": ObjectId(event_id), "store_id": {"$in": [store_id, store_id_obj]}},
            {"$set": update_fields}
        )

        if not result.matched_count:
            return jsonify({"message": "Event not found"}), 404

        return jsonify({"message": "Event updated"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@events_bp.route("/events/<event_id>", methods=["DELETE"])
@jwt_required
def delete_event(event_id):
    """Delete an event."""
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        
        try:
            store_id_obj = ObjectId(store_id)
        except:
            store_id_obj = store_id

        result = db.store_events.delete_one(
            {"_id": ObjectId(event_id), "store_id": {"$in": [store_id, store_id_obj]}}
        )

        if not result.deleted_count:
            return jsonify({"message": "Event not found"}), 404

        return jsonify({"message": "Event deleted"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500
