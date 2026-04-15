from pymongo import ASCENDING, DESCENDING
from datetime import datetime, timezone

def init_collections(db):
    # ── Products ──────────────────────────────────────────
    db.products.create_index([("sku", ASCENDING)], unique=True)
    db.products.create_index([("category", ASCENDING)])

    # ── Inventory ─────────────────────────────────────────
    db.inventory.create_index([("product_id", ASCENDING)], unique=True)
    db.inventory.create_index([("stock_status", ASCENDING)])

    # ── Sales ─────────────────────────────────────────────
    db.sales.create_index([("created_at", DESCENDING)])
    db.sales.create_index([("product_id", ASCENDING)])

    # ── Alerts ────────────────────────────────────────────
    db.alerts.create_index([("status", ASCENDING)])
    db.alerts.create_index([("created_at", DESCENDING)])

    # ── Reorder Orders ────────────────────────────────────
    db.reorder_orders.create_index([("store_id", ASCENDING)])
    db.reorder_orders.create_index([("status", ASCENDING)])
    db.reorder_orders.create_index([("created_at", DESCENDING)])

    # ── Reorder Settings ──────────────────────────────────
    db.reorder_settings.create_index([("store_id", ASCENDING)], unique=True)

    # ── Invoices ──────────────────────────────────────────
    db.invoices.create_index([("store_id", ASCENDING)])
    db.invoices.create_index([("created_at", DESCENDING)])
    db.invoices.create_index([("status", ASCENDING)])

    # ── Activity Log ──────────────────────────────────────
    db.activity_log.create_index([("store_id", ASCENDING)])
    db.activity_log.create_index([("created_at", DESCENDING)])

    print("✅ All collection indexes created")


# ── Document builders (use these in routes) ───────────────
def new_product(name, sku, category, unit, cost_price, selling_price, emoji, safety_stock, reorder_point, store_id):
    return {
        "name": name,
        "sku": sku,
        "category": category,
        "unit": unit,

        # 🔥 NEW (core fix)
        "cost_price": cost_price,
        "selling_price": selling_price,

        "emoji": emoji,
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "store_id": store_id,

        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

def new_inventory(product_id, stock, predicted_sales=0):
    status = (
        "Out of Stock" if stock == 0 else
        "Low Stock"    if stock < 10 else
        "Healthy"
    )
    return {
        "product_id": product_id, "stock": stock,
        "predicted_sales": predicted_sales,
        "stock_status": status,
        "last_updated": datetime.now(timezone.utc),
    }

def new_alert(product_id, product_name, alert_type, message, severity):
    return {
        "product_id": product_id, "product_name": product_name,
        "type": alert_type, "message": message,
        "severity": severity,  # critical | warning | info
        "status": "active",    # active | dismissed | resolved
        "created_at": datetime.now(timezone.utc),
    }

def new_reorder_order(product_id, product_name, qty, urgency, est_cost):
    return {
        "product_id": product_id, "product_name": product_name,
        "reorder_qty": qty, "urgency": urgency,
        "est_cost": est_cost,
        "status": "pending",   # pending | approved | dismissed
        "created_at": datetime.now(timezone.utc),
    }

def new_invoice(filename, raw_text, parsed_items, total_amount, status="pending"):
    return {
        "filename": filename, "raw_text": raw_text,
        "parsed_items": parsed_items, "total_amount": total_amount,
        "status": status,  # pending | verified | rejected
        "created_at": datetime.now(timezone.utc),
    }