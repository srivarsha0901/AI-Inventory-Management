from datetime import datetime, timezone, timedelta
import random
from models import new_product, new_inventory, new_alert, new_reorder_order

GROCERY_PRODUCTS = [
    ("Full Cream Milk",   "DAIRY-001", "Dairy",      "L",      42,  62,  "🥛", 20, 30),
    ("Greek Yogurt",      "DAIRY-002", "Dairy",      "cups",   60,  85,  "🍶", 15, 25),
    ("Butter Salted",     "DAIRY-003", "Dairy",      "packs",  38,  55,  "🧈", 10, 20),
    ("Paneer Fresh",      "DAIRY-004", "Dairy",      "kg",     85,  120, "🧀", 8,  15),
    ("Croissant",         "BAKERY-001","Bakery",     "pcs",    30,  45,  "🥐", 15, 25),
    ("Sourdough Bread",   "BAKERY-002","Bakery",     "loaves", 65,  95,  "🍞", 20, 30),
    ("Whole Wheat Bread", "BAKERY-003","Bakery",     "loaves", 30,  45,  "🍞", 20, 30),
    ("Mango Alphonso",    "FRUIT-001", "Fruits",     "kg",     80,  120, "🥭", 25, 40),
    ("Bananas",           "FRUIT-002", "Fruits",     "dozen",  25,  40,  "🍌", 20, 35),
    ("Tomatoes",          "VEG-001",   "Vegetables", "kg",     18,  30,  "🍅", 20, 35),
    ("Spinach",           "VEG-002",   "Vegetables", "bunches",15,  25,  "🥬", 15, 25),
    ("Onions",            "VEG-003",   "Vegetables", "kg",     22,  35,  "🧅", 25, 40),
    ("Potatoes",          "VEG-004",   "Vegetables", "kg",     18,  28,  "🥔", 30, 50),
    ("Basmati Rice 5kg",  "GRAIN-001", "Grains",     "bags",   240, 320, "🌾", 10, 20),
    ("Atta Wheat 10kg",   "GRAIN-002", "Grains",     "bags",   200, 280, "🌾", 8,  15),
    ("Sunflower Oil 1L",  "OIL-001",   "Oils",       "bottles",110, 145, "🫙", 12, 20),
    ("Mustard Oil 1L",    "OIL-002",   "Oils",       "bottles",100, 135, "🫙", 10, 18),
    ("Orange Juice 1L",   "BEV-001",   "Beverages",  "bottles",65,  95,  "🍊", 15, 25),
    ("Coconut Water",     "BEV-002",   "Beverages",  "cans",   30,  45,  "🥥", 20, 35),
    ("Eggs (12 pack)",    "EGG-001",   "Eggs",       "packs",  60,  85,  "🥚", 15, 25),
]

def seed_all(db, store_id=None):
    """Seed demo data. If store_id is provided, all data is scoped to that store."""
    _seed_products_and_inventory(db, store_id)
    _seed_alerts(db, store_id)
    _seed_reorder_orders(db, store_id)
    _seed_sales(db, store_id)
    print("✅ All collections seeded" + (f" for store {store_id}" if store_id else ""))

def _seed_products_and_inventory(db, store_id=None):
    query = {"store_id": store_id} if store_id else {}
    if db.products.count_documents(query) > 0:
        return

    now = datetime.now(timezone.utc)
    for name, sku, category, unit, cost_price, selling_price, emoji, safety, reorder_pt in GROCERY_PRODUCTS:
        product = {
            "name": name, "sku": sku, "category": category,
            "unit": unit, "cost_price": cost_price, "selling_price": selling_price,
            "emoji": emoji, "safety_stock": safety, "reorder_point": reorder_pt,
            "is_active": True, "created_at": now,
        }
        if store_id:
            product["store_id"] = store_id

        result = db.products.insert_one(product)
        product_id = result.inserted_id

        stock = random.randint(2, 60)
        predicted = random.randint(10, 80)
        status = (
            "Out of Stock" if stock == 0 else
            "Low Stock"    if stock < safety else
            "Healthy"
        )
        inv_doc = {
            "product_id": product_id,
            "product_name": name,
            "sku": sku,
            "category": category,
            "emoji": emoji,
            "unit": unit,
            "stock": stock,
            "predicted_sales": predicted,
            "safety_stock": safety,
            "reorder_point": reorder_pt,
            "stock_status": status,
            "last_updated": now,
        }
        if store_id:
            inv_doc["store_id"] = store_id
        db.inventory.insert_one(inv_doc)

    print(f"🌱 Seeded {len(GROCERY_PRODUCTS)} products + inventory")

def _seed_alerts(db, store_id=None):
    query = {"store_id": store_id} if store_id else {}
    if db.alerts.count_documents(query) > 0:
        return

    now = datetime.now(timezone.utc)
    sample_alerts = [
        ("Full Cream Milk",  "low_stock", "Only 4 units left — below safety stock of 20", "critical"),
        ("Mango Alphonso",   "expiry",    "12 kg expires today — mark for discount",       "critical"),
        ("Croissant",        "low_stock", "8 pcs left — below reorder point of 25",        "critical"),
        ("Sourdough Bread",  "expiry",    "28 loaves expire tomorrow",                      "warning"),
        ("Greek Yogurt",     "low_stock", "6 cups left — suggested reorder: 40",           "warning"),
        ("Spinach",          "low_stock", "15 bunches left — suggested reorder: 50",       "warning"),
        ("Butter Salted",    "expiry",    "Expires in 3 days — 22 packs",                  "warning"),
        ("Orange Juice 1L",  "low_stock", "Stock running low — 9 bottles remaining",       "info"),
    ]

    for name, atype, msg, severity in sample_alerts:
        doc = {
            "product_name": name,
            "type": atype,
            "message": msg,
            "severity": severity,
            "status": "active",
            "created_at": now,
        }
        if store_id:
            doc["store_id"] = store_id
        db.alerts.insert_one(doc)

    print("🔔 Seeded alerts")

def _seed_reorder_orders(db, store_id=None):
    query = {"store_id": store_id} if store_id else {}
    if db.reorder_orders.count_documents(query) > 0:
        return

    now = datetime.now(timezone.utc)
    orders = [
        ("Full Cream Milk",  100, "critical", 6200),
        ("Croissant",        60,  "critical", 2700),
        ("Greek Yogurt",     80,  "high",     6800),
        ("Spinach",          60,  "high",     1500),
        ("Mango Alphonso",   120, "medium",   14400),
        ("Sourdough Bread",  80,  "medium",   7600),
        ("Basmati Rice 5kg", 20,  "low",      6400),
    ]

    for name, qty, urgency, cost in orders:
        doc = {
            "product_name": name,
            "reorder_qty": qty,
            "urgency": urgency,
            "est_cost": cost,
            "status": "pending",
            "created_at": now,
        }
        if store_id:
            doc["store_id"] = store_id
        db.reorder_orders.insert_one(doc)

    print("📦 Seeded reorder orders")

def _seed_sales(db, store_id=None):
    query = {"store_id": store_id} if store_id else {}
    if db.sales.count_documents(query) > 0:
        return

    now = datetime.now(timezone.utc)
    products = [
        ("Full Cream Milk", 62),
        ("Bananas", 40),
        ("Tomatoes", 30),
        ("Eggs (12 pack)", 85),
        ("Basmati Rice 5kg", 320),
    ]
    for i in range(30):
        for product_name, price in products:
            qty = random.randint(5, 50)
            total = qty * price
            doc = {
                "product_name": product_name,
                "items": [{
                    "name": product_name,
                    "qty": qty,
                    "unit_price": price,
                }],
                "subtotal": total,
                "tax": round(total * 0.05, 2),
                "total": round(total * 1.05, 2),
                "created_at": now - timedelta(days=i),
            }
            if store_id:
                doc["store_id"] = store_id
                doc["cashier_id"] = "seed"
            db.sales.insert_one(doc)

    print("💰 Seeded sales history (30 days)")