from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from datetime import datetime, timezone

seasonal_bp = Blueprint("seasonal", __name__)

INDIAN_FESTIVALS = [
    { "name": "Diwali",     "month": 10, "boost_categories": ["Sweets","Snacks","Oils","Beverages"], "multiplier": 1.8 },
    { "name": "Christmas",  "month": 12, "boost_categories": ["Bakery","Beverages","Dairy","Eggs"],  "multiplier": 1.6 },
    { "name": "Holi",       "month": 3,  "boost_categories": ["Beverages","Dairy","Snacks"],         "multiplier": 1.4 },
    { "name": "Eid",        "month": 4,  "boost_categories": ["Grains","Dairy","Oils"],              "multiplier": 1.5 },
    { "name": "Pongal",     "month": 1,  "boost_categories": ["Grains","Dairy","Vegetables"],        "multiplier": 1.4 },
    { "name": "Navratri",   "month": 10, "boost_categories": ["Dairy","Fruits","Grains"],            "multiplier": 1.3 },
    { "name": "New Year",   "month": 1,  "boost_categories": ["Beverages","Bakery","Snacks"],        "multiplier": 1.5 },
]

@seasonal_bp.route("/seasonal/upcoming", methods=["GET"])
@jwt_required
def get_upcoming_festivals():
    now          = datetime.now(timezone.utc)
    current_month = now.month
    next_month    = (current_month % 12) + 1

    upcoming = [
        f for f in INDIAN_FESTIVALS
        if f["month"] in [current_month, next_month]
    ]

    return jsonify({"data": upcoming, "current_month": current_month})


@seasonal_bp.route("/seasonal/apply-boost", methods=["POST"])
@jwt_required
def apply_seasonal_boost():
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        data     = request.get_json()
        festival = data.get("festival")
        now      = datetime.now(timezone.utc)

        # Find the festival
        fest = next((f for f in INDIAN_FESTIVALS if f["name"] == festival), None)
        if not fest:
            return jsonify({"message": "Festival not found"}), 404

        # Apply boost to matching categories
        items = list(db.inventory.find({"store_id": store_id}))
        updated = 0
        for item in items:
            if item.get("category") in fest["boost_categories"]:
                current_pred = item.get("predicted_sales", 0)
                if current_pred > 0:
                    boosted = round(current_pred * fest["multiplier"], 2)
                    db.inventory.update_one(
                        {"_id": item["_id"]},
                        {"$set": {
                            "predicted_sales":    boosted,
                            "seasonal_boost":     fest["name"],
                            "seasonal_multiplier": fest["multiplier"],
                            "last_updated":       now,
                        }}
                    )
                    updated += 1

        return jsonify({
            "message":  f"✅ Applied {fest['name']} boost ({fest['multiplier']}×) to {updated} products",
            "festival": fest["name"],
            "updated":  updated,
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# ── Seasonal Product Suggestions ───────────────────────────────────

SEASONAL_PRODUCTS = {
    # month → list of (product_name, category, reason, emoji)
    1:  [("Til Ladoo","Sweets","Makar Sankranti — sesame sweets high demand","🍬"),
         ("Jaggery","Sweets","Winter staple + festival season","🫙"),
         ("Green Peas","Vegetables","Peak winter season, very fresh","🫛"),
         ("Carrots","Vegetables","Peak season — gajar ka halwa","🥕"),
         ("Oranges","Fruits","Best citrus season in India","🍊"),
         ("Peanuts","Snacks","Lohri/Sankranti — roasted peanut demand 3×","🥜")],
    2:  [("Strawberries","Fruits","Short season Feb-Mar, high margin","🍓"),
         ("Spinach","Vegetables","Peak winter greens, demand peaks","🥬"),
         ("Cauliflower","Vegetables","Winter peak — best prices now","🥦")],
    3:  [("Thandai Mix","Beverages","Holi special — 5× demand spike","🥛"),
         ("Food Colors","Other","Holi essential","🎨"),
         ("Gujiyas","Bakery","Holi sweet — very high margin","🥟"),
         ("Mango Raw","Fruits","Early mango season starts","🥭"),
         ("Buttermilk","Dairy","Summer starting — chilled drinks peak","🥛")],
    4:  [("Mango Alphonso","Fruits","Peak mango season — highest demand product","🥭"),
         ("Watermelon","Fruits","Summer essential — fast seller","🍉"),
         ("Coconut Water","Beverages","Summer heat drives 4× demand","🥥"),
         ("Ice Cream","Dairy","Summer — stock up cold items","🍦"),
         ("Yogurt","Dairy","Lassi/raita demand peaks in summer","🍶"),
         ("Dates","Fruits","Ramadan — high demand for iftar","🌴")],
    5:  [("Mango Varieties","Fruits","Peak season for Dasheri, Langra","🥭"),
         ("Litchi","Fruits","Short season May-Jun, premium price","🍈"),
         ("Nimbu Pani Mix","Beverages","Lemonade season — fast seller","🍋"),
         ("Curd","Dairy","Summer curd consumption peaks","🥛")],
    6:  [("Corn Fresh","Vegetables","Monsoon starts — bhutta season","🌽"),
         ("Pakora Mix","Grains","Monsoon special — chai + pakora","📦"),
         ("Ginger","Vegetables","Monsoon immunity — demand rises","🫚"),
         ("Tea Leaves","Beverages","Chai consumption spikes in monsoon","🍵")],
    7:  [("Turmeric","Other","Monsoon immunity booster demand","📦"),
         ("Honey","Other","Cold/monsoon health product","🍯"),
         ("Mushrooms","Vegetables","Monsoon growth season — fresh and cheap","🍄"),
         ("Onions","Vegetables","Pre-monsoon stock up before prices rise","🧅")],
    8:  [("Sabudana","Grains","Shravan/fasting month — 3× demand","📦"),
         ("Rock Salt","Other","Vrat season essential","🧂"),
         ("Potato","Vegetables","Fasting-friendly food demand rises","🥔"),
         ("Banana","Fruits","Year-round but fasting demand peaks","🍌")],
    9:  [("Sweet Potatoes","Vegetables","Navratri fasting essential","🍠"),
         ("Dry Fruits Mix","Snacks","Pre-Diwali gifting starts","🥜"),
         ("Ghee","Oils","Festival cooking season begins","🫙")],
    10: [("Sweets Assorted","Sweets","Diwali — biggest sales month","🍬"),
         ("Dry Fruits","Snacks","Diwali gifting — premium boxes","🥜"),
         ("Refined Oil 5L","Oils","Festival cooking — bulk demand","🛢️"),
         ("Sugar","Grains","Sweet-making season demand 2×","📦"),
         ("Milk Full Cream","Dairy","Sweet preparation drives 3× demand","🥛"),
         ("Ghee 1kg","Oils","Festival essential — very high margin","🫙")],
    11: [("Root Vegetables","Vegetables","Winter crops arriving","🥕"),
         ("Mustard Oil","Oils","North India winter cooking essential","🫙"),
         ("Methi (Fenugreek)","Vegetables","Winter green — peak season","🥬")],
    12: [("Cake Mix","Bakery","Christmas/New Year party demand","🎂"),
         ("Plum Cake","Bakery","Christmas special — premium pricing","🍰"),
         ("Cheese","Dairy","Party season — pizza/sandwich demand","🧀"),
         ("Soft Drinks","Beverages","Party/celebration stock up","🥤"),
         ("Paneer","Dairy","Winter + party season — highest demand","🧀"),
         ("Eggs","Eggs","Winter protein demand + baking season","🥚")],
}

REGION_PRODUCTS = {
    "north":  [("Sarson ka Saag Mix","Vegetables","Winter North India staple","🥬"),
               ("Makki Atta","Grains","Goes with saag — seasonal pair","🌾")],
    "south":  [("Coconut","Fruits","South Indian cooking essential","🥥"),
               ("Curry Leaves","Vegetables","Year-round but peak usage","🌿"),
               ("Tamarind","Other","Sambar/rasam base — stock up","📦")],
    "east":   [("Mustard Seeds","Other","Bengali cooking staple","📦"),
               ("Fish Fresh","Other","East India — high demand","🐟")],
    "west":   [("Jaggery (Gur)","Sweets","Gujarati/Maharashtrian cuisine","🫙"),
               ("Kokum","Other","Konkan region summer cooler","📦")],
}


@seasonal_bp.route("/seasonal/suggestions", methods=["GET"])
@jwt_required
def get_seasonal_suggestions():
    """Suggest products to add to inventory based on current season and region."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        now      = datetime.now(timezone.utc)
        month    = now.month
        region   = request.args.get("region", "").lower()

        # Get existing product names to avoid suggesting already-stocked items
        existing = set()
        for inv in db.inventory.find({"store_id": store_id}, {"product_name": 1}):
            existing.add(inv.get("product_name", "").lower())

        suggestions = []

        # Month-based suggestions
        for name, category, reason, emoji in SEASONAL_PRODUCTS.get(month, []):
            if name.lower() not in existing:
                suggestions.append({
                    "product_name": name,
                    "category":     category,
                    "reason":       reason,
                    "emoji":        emoji,
                    "type":         "seasonal",
                    "priority":     "high",
                })

        # Next month preview
        next_month = (month % 12) + 1
        for name, category, reason, emoji in SEASONAL_PRODUCTS.get(next_month, [])[:3]:
            if name.lower() not in existing:
                suggestions.append({
                    "product_name": name,
                    "category":     category,
                    "reason":       f"Coming next month — {reason}",
                    "emoji":        emoji,
                    "type":         "upcoming",
                    "priority":     "medium",
                })

        # Region-based suggestions
        if region and region in REGION_PRODUCTS:
            for name, category, reason, emoji in REGION_PRODUCTS[region]:
                if name.lower() not in existing:
                    suggestions.append({
                        "product_name": name,
                        "category":     category,
                        "reason":       reason,
                        "emoji":        emoji,
                        "type":         "regional",
                        "priority":     "medium",
                    })

        # Upcoming festivals
        upcoming_festivals = [
            f for f in INDIAN_FESTIVALS
            if f["month"] in [month, next_month]
        ]

        return jsonify({
            "data":      suggestions,
            "month":     month,
            "season":    _get_season(month),
            "festivals": upcoming_festivals,
            "total":     len(suggestions),
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@seasonal_bp.route("/seasonal/notifications", methods=["GET"])
@jwt_required
def get_notifications():
    """Combined notifications: stock alerts + seasonal suggestions + festival reminders."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        now      = datetime.now(timezone.utc)
        month    = now.month
        next_month = (month % 12) + 1

        notifications = []

        # 1. Upcoming festival alerts
        for fest in INDIAN_FESTIVALS:
            if fest["month"] == month:
                notifications.append({
                    "type":     "festival",
                    "priority": "high",
                    "icon":     "🎉",
                    "title":    f"{fest['name']} is this month!",
                    "message":  f"Stock up on {', '.join(fest['boost_categories'])} — expected {fest['multiplier']}× demand boost",
                    "action":   "Apply Boost",
                    "action_data": fest["name"],
                })
            elif fest["month"] == next_month:
                notifications.append({
                    "type":     "festival_upcoming",
                    "priority": "medium",
                    "icon":     "📅",
                    "title":    f"{fest['name']} is next month",
                    "message":  f"Start preparing: {', '.join(fest['boost_categories'])} will see higher demand",
                    "action":   None,
                })

        # 2. Seasonal product suggestions (top 5)
        existing = set()
        for inv in db.inventory.find({"store_id": store_id}, {"product_name": 1}):
            existing.add(inv.get("product_name", "").lower())

        season_items = SEASONAL_PRODUCTS.get(month, [])
        new_suggestions = [s for s in season_items if s[0].lower() not in existing]
        if new_suggestions:
            names = ", ".join(s[0] for s in new_suggestions[:4])
            notifications.append({
                "type":     "seasonal_suggestion",
                "priority": "medium",
                "icon":     "🌿",
                "title":    f"{len(new_suggestions)} seasonal products to consider",
                "message":  f"This month's trending: {names}. These are in high demand right now!",
                "action":   "View Suggestions",
            })

        # 3. Shelf life warnings for perishable items
        perishable = list(db.inventory.find({
            "store_id": store_id,
            "shelf_life_days": {"$gt": 0, "$lte": 3},
            "stock": {"$gt": 0},
        }))
        if perishable:
            names = ", ".join(p.get("product_name", "?") for p in perishable[:3])
            notifications.append({
                "type":     "perishable_warning",
                "priority": "high",
                "icon":     "⏰",
                "title":    f"{len(perishable)} highly perishable items in stock",
                "message":  f"{names} — shelf life ≤3 days. Ensure these sell quickly or reduce order qty.",
                "action":   None,
            })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        notifications.sort(key=lambda n: priority_order.get(n["priority"], 2))

        return jsonify({
            "data":    notifications,
            "total":   len(notifications),
            "season":  _get_season(month),
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500


def _get_season(month):
    if month in [3, 4, 5]:
        return "Summer"
    elif month in [6, 7, 8, 9]:
        return "Monsoon"
    elif month in [10, 11]:
        return "Autumn"
    else:
        return "Winter"