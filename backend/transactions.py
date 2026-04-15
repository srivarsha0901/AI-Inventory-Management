"""
MongoDB transaction handling for multi-step operations.
Ensures data consistency across multiple documents.
"""

from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.errors import OperationFailure, DuplicateKeyError
from functools import wraps
from typing import Callable, Any, Optional, Dict
import traceback


class TransactionManager:
    """Handles MongoDB transactions for critical operations."""
    
    def __init__(self, client: MongoClient, db=None):
        """Initialize with MongoDB client and optional database instance."""
        self.client = client
        self.db = db or client.get_database()
    
    @contextmanager
    def transaction(self, session=None):
        """Context manager for transactions."""
        if session is None:
            session = self.client.start_session()
            own_session = True
        else:
            own_session = False
        
        try:
            session.start_transaction()
            yield session
            session.commit_transaction()
        except Exception as e:
            session.abort_transaction()
            raise
        finally:
            if own_session:
                session.end_session()
    
    def execute_transaction(self, operation: Callable, *args, **kwargs) -> tuple:
        """
        Execute a function within a transaction.
        
        Args:
            operation: Async function to execute
            *args: Arguments to pass to operation
            **kwargs: Keyword arguments to pass to operation
        
        Returns:
            Tuple of (success: bool, result: Any, error: Optional[str])
        """
        session = self.client.start_session()
        try:
            with self.transaction(session):
                result = operation(*args, **kwargs, session=session)
            return True, result, None
        except DuplicateKeyError as e:
            return False, None, f"Duplicate entry: {str(e)}"
        except OperationFailure as e:
            return False, None, f"Operation failed: {str(e)}"
        except Exception as e:
            return False, None, f"Transaction failed: {str(e)}"
        finally:
            session.end_session()


# ✅ REORDER DELIVERY TRANSACTION
def transaction_reorder_delivery(db, order_id: str, received_qty: int, session) -> Dict:
    """
    Atomic transaction for marking reorder as delivered.
    
    Steps:
    1. Update reorder_orders status to 'delivered'
    2. Increment inventory stock
    3. Record activity log
    
    Rollback on failure ensures no partial updates.
    """
    from bson.objectid import ObjectId
    from datetime import datetime
    
    try:
        order_oid = ObjectId(order_id)
    except:
        raise ValueError(f"Invalid order ID: {order_id}")
    
    # Step 1: Update reorder order status
    order_update = db.reorder_orders.find_one_and_update(
        {"_id": order_oid, "status": "approved"},
        {
            "$set": {
                "status": "delivered",
                "received_qty": received_qty,
                "delivered_at": datetime.utcnow(),
            }
        },
        return_document=True,
        session=session
    )
    
    if not order_update:
        raise ValueError("Order not found or not in 'approved' status")
    
    # Step 2: Increment inventory stock atomically
    store_id = order_update.get("store_id")
    product_id = order_update.get("product_id")
    
    inventory_update = db.inventory.find_one_and_update(
        {"_id": ObjectId(product_id), "store_id": store_id},
        {"$inc": {"stock": received_qty}},
        return_document=True,
        session=session
    )
    
    if not inventory_update:
        raise ValueError(f"Inventory not found for product {product_id}")
    
    # Step 3: Record activity log
    db.activity_log.insert_one({
        "store_id": store_id,
        "action": "reorder_delivered",
        "details": {
            "order_id": order_oid,
            "product_id": ObjectId(product_id),
            "quantity": received_qty,
            "previous_stock": inventory_update.get("stock", 0) - received_qty,
            "new_stock": inventory_update.get("stock", 0),
        },
        "created_at": datetime.utcnow(),
    }, session=session)
    
    return {
        "success": True,
        "order": order_update,
        "inventory": inventory_update,
    }


# ✅ SALE COMPLETION TRANSACTION
def transaction_complete_sale(db, sale_data: Dict, session) -> Dict:
    """
    Atomic transaction for completing a sale.
    
    Steps:
    1. Decrement inventory for each item (atomic $inc)
    2. Create sales record
    3. Check for low stock alerts
    4. Record activity log
    5. Update store statistics
    
    Rollback ensures inventory never corrupted.
    """
    from bson.objectid import ObjectId
    from datetime import datetime
    
    store_id = sale_data["store_id"]
    items = sale_data["items"]
    is_success = False
    
    # Step 1: Decrement inventory (atomic for each item)
    decremented_items = []
    for item in items:
        product_oid = ObjectId(item["product_id"])
        qty = int(item["qty"])
        
        inventory = db.inventory.find_one_and_update(
            {"_id": product_oid, "store_id": store_id},
            {"$inc": {"stock": -qty}},
            return_document=True,
            session=session
        )
        
        if not inventory:
            raise ValueError(f"Product {item['product_id']} not found")
        
        if inventory.get("stock", 0) < 0:
            raise ValueError(f"Insufficient stock for {item['product_id']}")
        
        decremented_items.append(inventory)
    
    # Step 2: Create sales record
    sale_record = {
        "store_id": store_id,
        "items": items,
        "subtotal": sale_data["subtotal"],
        "tax": sale_data["tax"],
        "total": sale_data["total"],
        "payment_method": sale_data.get("payment_method", "cash"),
        "created_at": datetime.utcnow(),
    }
    
    sale_result = db.sales.insert_one(sale_record, session=session)
    is_success = True
    
    # Step 3 & 4: Check for alerts and log
    for i, item in enumerate(decremented_items):
        reorder_point = item.get("reorder_point", item.get("safety_stock", 10))
        if item.get("stock", 0) <= reorder_point:
            # Check for recent duplicate alert
            recent_alert = db.alerts.find_one({
                "product_id": item["_id"],
                "store_id": store_id,
                "type": "low_stock",
                "created_at": {"$gte": datetime.utcnow().replace(hour=datetime.utcnow().hour-1)},
            }, session=session)
            
            if not recent_alert:
                db.alerts.insert_one({
                    "product_id": item["_id"],
                    "product_name": item.get("product_name", item.get("name", "Unknown")),
                    "store_id": store_id,
                    "type": "low_stock",
                    "message": f"{item.get('stock')} {item.get('unit', 'units')} left — below reorder point of {reorder_point}",
                    "severity": "critical" if item.get("stock", 0) == 0 else "warning",
                    "status": "active",
                    "created_at": datetime.utcnow(),
                }, session=session)
    
    # Step 5: Record activity
    db.activity_log.insert_one({
        "store_id": store_id,
        "action": "sale_completed",
        "details": {
            "sale_id": sale_result.inserted_id,
            "total": sale_data["total"],
            "items_count": len(items),
        },
        "created_at": datetime.utcnow(),
    }, session=session)
    
    return {
        "success": True,
        "sale_id": str(sale_result.inserted_id),
        "total": sale_data["total"],
    }


# ✅ ONBOARDING TRANSACTION
def transaction_onboard_inventory(db, store_id, items: list, session) -> Dict:
    """
    Atomic transaction for bulk inventory onboarding.
    
    Steps:
    1. Create/update products
    2. Create/update inventory records
    3. Create reorder settings (if new store)
    4. Record activity
    
    All-or-nothing: partial failures rollback entire import.
    """
    from bson.objectid import ObjectId
    from datetime import datetime
    
    created_count = 0
    updated_count = 0
    
    for item in items:
        # Step 1: Create or get product
        product_filter = {
            "store_id": store_id,
            "name": item["name"],
            "category": item["category"],
        }
        
        product = db.products.find_one(product_filter, session=session)
        
        if not product:
            # Create new product
            product_data = {
                "store_id": store_id,
                "name": item["name"],
                "category": item["category"],
                "unit": item["unit"],
                "cost_price": item["cost_price"],
                "selling_price": item["selling_price"],
                "shelf_life_days": item.get("shelf_life_days", 0),
                "restock_days": item.get("restock_days", 7),
                "emoji": item.get("emoji", "📦"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            result = db.products.insert_one(product_data, session=session)
            product_id = result.inserted_id
            created_count += 1
        else:
            product_id = product["_id"]
            updated_count += 1
        
        # Step 2: Create or update inventory
        inventory_filter = {
            "store_id": store_id,
            "product_id": product_id,
        }
        
        inventory_data = {
            "store_id": store_id,
            "product_id": product_id,
            "stock": item["stock"],
            "safety_stock": item.get("safety_stock", 10),
            "updated_at": datetime.utcnow(),
        }
        
        existing = db.inventory.find_one(inventory_filter, session=session)
        if not existing:
            inventory_data["created_at"] = datetime.utcnow()
            db.inventory.insert_one(inventory_data, session=session)
        else:
            db.inventory.update_one(inventory_filter, {"$set": inventory_data}, session=session)
    
    # Step 3: Create reorder settings if not exists
    reorder_settings = db.reorder_settings.find_one({"store_id": store_id}, session=session)
    if not reorder_settings:
        db.reorder_settings.insert_one({
            "store_id": store_id,
            "default_restock_days": 7,
            "safety_multiplier": 1.5,
            "auto_approve": False,
            "created_at": datetime.utcnow(),
        }, session=session)
    
    # Step 4: Record activity
    db.activity_log.insert_one({
        "store_id": store_id,
        "action": "inventory_onboarded",
        "details": {
            "created": created_count,
            "updated": updated_count,
            "total": len(items),
        },
        "created_at": datetime.utcnow(),
    }, session=session)
    
    return {
        "success": True,
        "created": created_count,
        "updated": updated_count,
        "total": len(items),
    }


# ✅ DECORATOR FOR TRANSACTION OPERATIONS
def with_transaction(transaction_func: Callable):
    """
    Decorator to wrap route handlers with transaction support.
    
    Usage:
        @with_transaction(transaction_complete_sale)
        def post_sale():
            return transaction_complete_sale(db, request.json, session)
    """
    @wraps(transaction_func)
    def wrapper(*args, **kwargs):
        try:
            return transaction_func(*args, **kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    return wrapper
