## Phase 3a: Developer Quick Reference

**How to Use Validation in Routes**

---

## 1. Quick Start

### Import the Validator
```python
from validation import SaleSchema, validate_request
```

### Add One Line to Your Route
```python
@app.route("/sales", methods=["POST"])
def create_sale():
    data = request.get_json()
    
    # ✅ ADD THIS LINE
    success, result = validate_request(SaleSchema, data)
    if not success:
        return jsonify(result), 400
    
    # result now contains validated & type-converted data
    validated_data = result
    
    # Use validated_data from here on
    sale_record = {
        "total": validated_data["total"],  # Always a float
        "items": validated_data["items"],  # Validated array
    }
```

---

## 2. What Each Schema Does

### RegisterSchema
```python
# Input:
{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "secure123",
    "store_name": "My Shop",
    "address": "123 Main St"  # Optional
}

# Output (if valid):
{
    "name": "John Doe",
    "email": "john@example.com",  # Lowercased
    "password": "secure123",
    "store_name": "My Shop",
    "address": "123 Main St"
}

# Error (if invalid):
{"error": "name must be at least 2 characters"}
```

### SaleSchema
```python
# Input:
{
    "items": [
        {"product_id": "abc123", "qty": 5},
        {"product_id": "def456", "qty": 3}
    ],
    "subtotal": 500,
    "tax": 50,
    "total": 550
}

# Output (if valid):
{
    "items": [
        {"product_id": "abc123", "qty": 5},
        {"product_id": "def456", "qty": 3}
    ],
    "subtotal": 500.0,  # Converted to float
    "tax": 50.0,
    "total": 550.0
}

# Error (if invalid):
{"error": "items[0].qty must be whole number"}
```

### StaffSchema
```python
# Input:
{
    "name": "Alice",
    "email": "alice@store.com",
    "password": "pass123"
}

# Output (if valid):
{
    "name": "Alice",
    "email": "alice@store.com",  # Lowercased
    "password": "pass123"
}

# Error (if invalid):
{"error": "email must be a valid email address"}
```

### ReorderDeliverySchema
```python
# Input:
{"received_qty": 100}

# Output (if valid):
{"received_qty": 100}  # Confirmed as whole number

# Error (if invalid):
{"error": "received_qty must be a whole number"}
```

### ReorderSettingsSchema
```python
# Input:
{
    "default_restock_days": 7,
    "safety_multiplier": 1.5,
    "auto_approve": false,
    "min_order_value": 500
}

# Output (if valid):
{
    "default_restock_days": 7,
    "safety_multiplier": 1.5,
    "auto_approve": false,
    "min_order_value": 500.0
}

# Error (if invalid):
{"error": "default_restock_days cannot be less than 1"}
```

---

## 3. All Validator Methods

### Validate String
```python
from validation import Validator

# usage:
value = Validator.validate_string(
    value="hello",
    field_name="username",
    min_len=1,
    max_len=50
)
# Returns: "hello"
# Raises: ValidationError if invalid
```

### Validate Number
```python
value = Validator.validate_number(
    value="42.5",
    field_name="price",
    min_val=0,
    max_val=1000,
    allow_negative=False
)
# Returns: 42.5 (converted to float)
# Raises: ValidationError if invalid
```

### Validate Email
```python
value = Validator.validate_email(
    value="user@example.com",
    field_name="email"
)
# Returns: "user@example.com" (lowercased)
# Raises: ValidationError if not valid format
```

### Validate Choice
```python
value = Validator.validate_choice(
    value="approved",
    field_name="status",
    choices=["pending", "approved", "dismissed"]
)
# Returns: "approved"
# Raises: ValidationError if not in choices
```

### Validate List
```python
value = Validator.validate_list(
    value=[1, 2, 3],
    field_name="items",
    min_items=1
)
# Returns: [1, 2, 3]
# Raises: ValidationError if empty or not a list
```

---

## 4. Error Handling Pattern

### Standard Pattern
```python
success, result = validate_request(SaleSchema, data)
if not success:
    # result is {"error": "descriptive message"}
    return jsonify(result), 400

# result is now the validated data
validated_data = result
```

### Error Response Examples

**Malformed Input**
```json
400 Bad Request
{"error": "items must be a list"}
```

**Range Violation**
```json
400 Bad Request
{"error": "price cannot exceed 1000000"}
```

**Type Mismatch**
```json
400 Bad Request
{"error": "qty must be a valid number"}
```

**Business Logic**
```json
400 Bad Request
{"error": "total (550) must equal subtotal (500) + tax (100)"}
```

---

## 5. Adding New Schemas

### Example: Creating a new ProductSchema
```python
# In validation.py:

class ProductSchema:
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, Dict]:
        try:
            return True, {
                "name": Validator.validate_string(data.get("name"), "name", min_len=1, max_len=200),
                "price": Validator.validate_number(data.get("price"), "price", min_val=0, max_val=1000000),
                "category": Validator.validate_string(data.get("category", "General"), "category"),
            }
        except ValidationError as e:
            return False, {"error": str(e)}

# In your route:
from validation import ProductSchema, validate_request

@app.route("/products", methods=["POST"])
def create_product():
    success, result = validate_request(ProductSchema, request.get_json())
    if not success:
        return jsonify(result), 400
    
    product = result  # Validated data ready to use
```

---

## 6. Common Mistakes to Avoid

### ❌ Don't Skip Validation
```python
# BAD - direct use of request data
total = request.json["total"]  # Could be string!
quantity = request.json["qty"]  # Could be 2.5!
```

### ✅ Do Validate First
```python
# GOOD - validate then use
success, result = validate_request(SaleSchema, request.json)
if not success:
    return jsonify(result), 400
total = result["total"]  # Always a float
quantity = result["qty"]  # Guaranteed whole number
```

### ❌ Don't Ignore Optional Fields
```python
# BAD - assumes address always present
address = validated_data["address"]  # KeyError if not in schema!
```

### ✅ Do Use .get() for Optional
```python
# GOOD - handle missing optional fields
address = validated_data.get("address", "")  # Default to empty string
```

### ❌ Don't Create New Validators
```python
# BAD - reinventing the wheel
if not email or "@" not in email:
    # Custom validation logic
```

### ✅ Do Use Existing Validators
```python
# GOOD - reuse EmailValidator
from validation import Validator
email = Validator.validate_email(data.get("email"), "email")
```

---

## 7. Testing Validation

### Unit Test Example
```python
def test_sale_validation():
    # Valid sale
    data = {
        "items": [{"product_id": "123", "qty": 5}],
        "subtotal": 500,
        "tax": 50,
        "total": 550
    }
    success, result = validate_request(SaleSchema, data)
    assert success == True
    assert result["total"] == 550.0
    
    # Invalid sale - qty not whole
    data["items"][0]["qty"] = 2.5
    success, result = validate_request(SaleSchema, data)
    assert success == False
    assert "whole number" in result["error"]
```

### Integration Test Example
```python
def test_create_sale_invalid():
    # Send invalid request
    response = client.post("/pos/sales", json={
        "items": [{"product_id": "123", "qty": 2.5}],
        "subtotal": 250,
        "tax": 25,
        "total": 275
    })
    
    # Check response
    assert response.status_code == 400
    assert "whole number" in response.json["error"]
```

---

## 8. Reference: All Field Constraints

### String Fields
| Field | Min | Max | Notes |
|-------|-----|-----|-------|
| name | 2 | 100 | Whitespace trimmed |
| email | 5 | 255 | Format validated |
| password | 6 | 200 | No format check |
| store_name | 2 | 200 | Required |
| address | 0 | 500 | Optional |

### Numeric Fields
| Field | Min | Max | Type |
|-------|-----|-----|------|
| price | 0 | 1M | Float |
| qty | 1 | 10K | Whole # |
| received_qty | 1 | 1M | Whole # |
| safety_stock | 0 | 100K | Float |
| restock_days | 1 | 90 | Integer |
| safety_multiplier | 0.5 | 5.0 | Float |

### Special Fields
| Field | Rule |
|-------|------|
| email | Must contain @ and . |
| total | Must equal subtotal + tax |
| qty | Must be whole number |
| received_qty | Must be whole number |
| emoji | 1-5 characters |

---

## 9. Debugging Validation Issues

### Check What's Being Rejected
```python
# If validation fails, print the error
success, result = validate_request(SaleSchema, data)
if not success:
    print(f"Validation Error: {result['error']}")
    # Shows: "Validation Error: items[0].qty must be whole number"
```

### Validate Each Field
```python
# Instead of debugging entire schema, check each field
from validation import Validator

try:
    name = Validator.validate_string(data.get("name"), "name", min_len=2)
    print(f"✅ Name valid: {name}")
except ValidationError as e:
    print(f"❌ Name invalid: {e}")
```

### Print Type Information
```python
# If number validation fails, check type
print(f"Value: {data['qty']}, Type: {type(data['qty'])}")
# Output: Value: 2.5, Type: <class 'float'>
# Error: "2.5 is a float, not whole number"
```

---

## 10. Integration Checklist

When adding validation to a new endpoint:

- [ ] Import required schema: `from validation import XyzSchema`
- [ ] Add validation check: `success, result = validate_request(XyzSchema, data)`
- [ ] Check for errors: `if not success: return jsonify(result), 400`
- [ ] Extract validated data: `validated_data = result`
- [ ] Use validated data in database operations
- [ ] Test with valid input (should work)
- [ ] Test with invalid input (should return 400)
- [ ] Check error message is helpful
- [ ] Update API documentation

---

**For Questions**: Reference `backend/validation.py` for all schema definitions
**For Issues**: Check that input types match schema expectations (string vs number)
