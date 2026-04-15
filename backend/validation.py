"""
Input validation schemas for FreshTrack API endpoints.
Uses simple dict-based validation (no external dependencies needed).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class Validator:
    """Base validator class."""
    
    @staticmethod
    def validate_string(value: Any, field_name: str, min_len: int = 1, max_len: int = 500) -> str:
        """Validate string field."""
        if value is None or not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        value = value.strip()
        if len(value) < min_len:
            raise ValidationError(f"{field_name} must be at least {min_len} characters")
        if len(value) > max_len:
            raise ValidationError(f"{field_name} cannot exceed {max_len} characters")
        return value
    
    @staticmethod
    def validate_number(value: Any, field_name: str, min_val: Optional[float] = None, 
                       max_val: Optional[float] = None, allow_negative: bool = False) -> float:
        """Validate numeric field."""
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number")
        
        if not allow_negative and value < 0:
            raise ValidationError(f"{field_name} cannot be negative")
        if min_val is not None and value < min_val:
            raise ValidationError(f"{field_name} cannot be less than {min_val}")
        if max_val is not None and value > max_val:
            raise ValidationError(f"{field_name} cannot exceed {max_val}")
        return value
    
    @staticmethod
    def validate_email(value: Any, field_name: str = "email") -> str:
        """Validate email address."""
        value = Validator.validate_string(value, field_name, min_len=5, max_len=255)
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValidationError(f"{field_name} must be a valid email address")
        return value.lower()
    
    @staticmethod
    def validate_choice(value: Any, field_name: str, choices: List[str]) -> str:
        """Validate value is in choices."""
        value = Validator.validate_string(value, field_name)
        if value not in choices:
            raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}")
        return value
    
    @staticmethod
    def validate_list(value: Any, field_name: str, min_items: int = 1) -> list:
        """Validate list field."""
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list")
        if len(value) < min_items:
            raise ValidationError(f"{field_name} must have at least {min_items} items")
        return value


# ✅ REGISTRATION SCHEMA
class RegisterSchema:
    """Validates user registration data."""
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        """Validate registration payload."""
        try:
            return True, {
                "name": Validator.validate_string(data.get("name"), "name", min_len=2, max_len=100),
                "email": Validator.validate_email(data.get("email")),
                "password": Validator.validate_string(data.get("password"), "password", min_len=6, max_len=200),
                "store_name": Validator.validate_string(data.get("store_name"), "store_name", min_len=2, max_len=200),
                "address": Validator.validate_string(data.get("address", ""), "address", min_len=0, max_len=500),
            }
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ SALE SCHEMA
class SaleSchema:
    """Validates POS sales data."""
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        """Validate sale payload."""
        try:
            items = Validator.validate_list(data.get("items", []), "items", min_items=1)
            
            # Validate each item
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    raise ValidationError(f"items[{i}] must be an object")
                
                Validator.validate_string(item.get("product_id", ""), f"items[{i}].product_id")
                qty = Validator.validate_number(item.get("qty", 1), f"items[{i}].qty", min_val=1, max_val=10000)
                if int(qty) != qty:
                    raise ValidationError(f"items[{i}].qty must be whole number")
            
            subtotal = Validator.validate_number(data.get("subtotal", 0), "subtotal", min_val=0)
            tax = Validator.validate_number(data.get("tax", 0), "tax", min_val=0)
            total = Validator.validate_number(data.get("total", 0), "total", min_val=0)
            
            # Verify total = subtotal + tax (within 1 rupee due to rounding)
            if abs((subtotal + tax) - total) > 1:
                raise ValidationError(f"total ({total}) must equal subtotal ({subtotal}) + tax ({tax})")
            
            return True, {
                "items": items,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
            }
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ INVENTORY ITEM SCHEMA
class InventoryItemSchema:
    """Validates inventory item for onboarding."""
    
    @staticmethod
    def validate(item: Dict) -> Tuple[bool, Dict]:
        """Validate single inventory item."""
        try:
            return True, {
                "name": Validator.validate_string(item.get("name", ""), "name", min_len=1, max_len=200),
                "category": Validator.validate_string(item.get("category", "General"), "category", max_len=50),
                "unit": Validator.validate_string(item.get("unit", "units"), "unit", max_len=20),
                "cost_price": Validator.validate_number(item.get("cost_price", 0), "cost_price", min_val=0, max_val=1000000),
                "selling_price": Validator.validate_number(item.get("selling_price", 0), "selling_price", min_val=0, max_val=1000000),
                "stock": Validator.validate_number(item.get("stock", 0), "stock", min_val=0, max_val=1000000),
                "safety_stock": Validator.validate_number(item.get("safety_stock", 10), "safety_stock", min_val=0, max_val=100000),
                "shelf_life_days": Validator.validate_number(item.get("shelf_life_days", 0), "shelf_life_days", min_val=0, max_val=3650),
                "restock_days": Validator.validate_number(item.get("restock_days", 7), "restock_days", min_val=1, max_val=90),
                "emoji": Validator.validate_string(item.get("emoji", "📦"), "emoji", min_len=1, max_len=5),
            }
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ INVENTORY BATCH SCHEMA
class InventoryBatchSchema:
    """Validates batch of inventory items for onboarding."""
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        """Validate inventory batch."""
        try:
            items = Validator.validate_list(data.get("items", []), "items", min_items=1)
            
            validated_items = []
            for i, item in enumerate(items):
                success, result = InventoryItemSchema.validate(item)
                if not success:
                    raise ValidationError(f"Item {i+1}: {result['error']}")
                validated_items.append(result)
            
            return True, {"items": validated_items}
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ STAFF CREATION SCHEMA
class StaffSchema:
    """Validates staff/cashier creation data."""
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        """Validate staff creation payload."""
        try:
            return True, {
                "name": Validator.validate_string(data.get("name"), "name", min_len=2, max_len=100),
                "email": Validator.validate_email(data.get("email")),
                "password": Validator.validate_string(data.get("password"), "password", min_len=6, max_len=200),
            }
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ REORDER DELIVERY SCHEMA
class ReorderDeliverySchema:
    """Validates reorder delivery data."""
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        """Validate reorder delivery."""
        try:
            received_qty = Validator.validate_number(
                data.get("received_qty", 0), 
                "received_qty", 
                min_val=1, 
                max_val=1000000
            )
            
            # Ensure whole number
            if int(received_qty) != received_qty:
                raise ValidationError("received_qty must be a whole number")
            
            return True, {"received_qty": int(received_qty)}
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ REORDER SETTINGS SCHEMA
class ReorderSettingsSchema:
    """Validates reorder configuration."""
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        """Validate reorder settings."""
        try:
            return True, {
                "default_restock_days": int(Validator.validate_number(
                    data.get("default_restock_days", 7), 
                    "default_restock_days", 
                    min_val=1, 
                    max_val=90
                )),
                "safety_multiplier": Validator.validate_number(
                    data.get("safety_multiplier", 1.5), 
                    "safety_multiplier", 
                    min_val=0.5, 
                    max_val=5.0
                ),
                "auto_approve": bool(data.get("auto_approve", False)),
                "min_order_value": Validator.validate_number(
                    data.get("min_order_value", 500), 
                    "min_order_value", 
                    min_val=0, 
                    max_val=1000000
                ),
            }
        except ValidationError as e:
            return False, {"error": str(e)}


# ✅ HELPER FUNCTION FOR ROUTES
def validate_request(schema_class, data: Dict) -> Tuple[bool, Dict]:
    """Generic validation helper for routes."""
    return schema_class.validate(data)


# Example usage in routes:
# success, result = validate_request(SaleSchema, request.get_json())
# if not success:
#     return jsonify(result), 400
# validated_data = result
