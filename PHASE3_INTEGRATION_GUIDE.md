# FreshTrack Phase 3 - Integration Quick Reference
**For Developers: How to Use the New Modules**

---

## 🎯 Quick Start (3 Minutes)

### 1. Input Validation
```python
from validation import validate_request, SaleSchema

# In your route:
@app.route('/pos/sales', methods=['POST'])
def create_sale():
    schema = SaleSchema()
    is_valid, error = validate_request(request.json, schema)
    
    if not is_valid:
        return {"error": error}, 400  # Auto-rejects invalid data
    
    # Continue with valid data...
```

### 2. Atomic Transactions
```python
from transactions import TransactionManager, transaction_complete_sale

@app.route('/pos/sales', methods=['POST'])
def create_sale():
    manager = TransactionManager()
    success, result, error = transaction_complete_sale(
        db, 
        store_id,
        sale_data
    )
    
    if not success:
        return {"error": error}, 500
    
    return {"sale": result}, 201
```

### 3. Caching & Rate Limiting
```python
from caching import get_cache, get_rate_limiter

@app.route('/dashboard/stats', methods=['GET'])
def get_stats():
    # Rate limiting is applied automatically in middleware
    
    cache = get_cache()
    cached = cache.get(f"dashboard_stats:{store_id}")
    
    if cached:
        return cached
    
    # Query DB
    stats = calculate_stats(...)
    cache.set(f"dashboard_stats:{store_id}", stats, ttl=300)
    
    return stats
```

---

## 📚 MODULE REFERENCE

### validation.py

**Usage**: Validate incoming API requests

```python
from validation import RegisterSchema, SaleSchema, StaffSchema

# Create schema instance
schema = RegisterSchema()

# Validate data
is_valid, error_dict = schema.validate(request.json)

if is_valid:
    # Process request
else:
    # error_dict contains field-specific errors
    return {"errors": error_dict}, 400
```

**Available Schemas**:
- `RegisterSchema` - email, password
- `SaleSchema` - items array, tax calculation
- `InventoryItemSchema` - product data
- `BatchInventorySchema` - bulk CSV data
- `StaffSchema` - employee data
- `ReorderDeliverySchema` - delivery quantity
- `ReorderSettingsSchema` - min stock, reorder qty

**Validator Methods**:
```python
# Use in custom schemas
Validator.validate_string(value, min_len=1, max_len=255)
Validator.validate_number(value, min_val=0, max_val=1000)
Validator.validate_email(value)
Validator.validate_choice(value, choices=["A", "B", "C"])
Validator.validate_list(value, min_items=1, max_items=100)
```

---

### transactions.py

**Usage**: Execute atomic multi-step operations

```python
from transactions import TransactionManager, transaction_complete_sale

# Create manager
manager = TransactionManager()

# Execute transaction
success, result, error = transaction_complete_sale(
    db,              # MongoDB connection
    store_id,        # Store context
    sale_data        # Sale information
)

if success:
    # All steps completed atomically
    return result
else:
    # Automatic rollback occurred
    return error
```

**Available Transactions**:

1. `transaction_reorder_delivery(db, store_id, delivery_data)`
   - Updates order status
   - Increments inventory
   - Logs activity
   - Returns: (success, delivery_result, error)

2. `transaction_complete_sale(db, store_id, sale_data)`
   - Decrements inventory items
   - Creates sale record
   - Checks for low stock items
   - Creates alerts if needed
   - Logs activity
   - Returns: (success, sale_result, error)

3. `transaction_onboard_inventory(db, store_id, items_data)`
   - Creates/updates inventory items
   - Creates/updates inventory records
   - Ensures reorder settings exist
   - Logs activity
   - Returns: (success, onboarding_result, error)

---

### caching.py

**Usage**: Cache data + rate limit requests

```python
from caching import get_cache, get_rate_limiter, init_cache

# Initialize (usually in app.py)
init_cache()  # Connects to Redis or uses in-memory

# Get cache instance
cache = get_cache()

# Set value (5-minute TTL)
cache.set("my_key", {"data": "value"}, ttl=300)

# Get value
value = cache.get("my_key")

# Delete value
cache.delete("my_key")

# Rate limiting (automatic in middleware, but can check manually)
limiter = get_rate_limiter()
allowed = limiter.is_allowed(user_id)
```

**Cache Features**:
- `set(key, value, ttl=300)` - Store with TTL
- `get(key)` - Retrieve (returns None if expired/missing)
- `delete(key)` - Remove immediately
- `clear()` - Clear all cache
- `get_redis_client()` - Direct Redis access if needed

**Rate Limiter Features**:
- `is_allowed(identifier)` - Check if request allowed
- Default: 100 requests/minute per identifier
- Configurable via RATE_LIMIT_RPM env var

**Batch Processor**:
```python
from caching import BatchProcessor

processor = BatchProcessor(batch_size=500)
def process_batch(items):
    # Process 500 items at a time
    return result

results = processor.process_batches(
    all_items,
    process_batch,
    on_progress=lambda done, total: print(f"{done}/{total}")
)
```

---

## 🔌 INTEGRATION EXAMPLES

### Example 1: Add New Endpoint with Validation

```python
from validation import InventoryItemSchema, validate_request

@app.route('/inventory/items', methods=['POST'])
def create_item():
    # Step 1: Validate
    schema = InventoryItemSchema()
    is_valid, error = validate_request(request.json, schema)
    
    if not is_valid:
        return {"error": error}, 400
    
    # Step 2: Process
    item = db.inventory.insert_one(request.json)
    
    # Step 3: Invalidate cache (if needed)
    cache = get_cache()
    cache.delete(f"inventory_list:{store_id}")
    
    return {"id": str(item.inserted_id)}, 201
```

### Example 2: Add New Endpoint with Transaction

```python
from transactions import TransactionManager
from validation import MySchema, validate_request

@app.route('/my-endpoint', methods=['POST'])
def my_endpoint():
    # Step 1: Validate
    schema = MySchema()
    is_valid, error = validate_request(request.json, schema)
    if not is_valid:
        return {"error": error}, 400
    
    # Step 2: Execute transaction
    manager = TransactionManager()
    success, result, error = manager.transaction_my_operation(
        db,
        store_id,
        request.json
    )
    
    if not success:
        return {"error": error}, 500
    
    # Step 3: Invalidate cache
    cache = get_cache()
    cache.delete(f"cache_key")
    
    return {"data": result}, 200
```

### Example 3: Add Cached Endpoint

```python
from caching import get_cache

@app.route('/my-stats', methods=['GET'])
def get_stats():
    # Rate limiting applied automatically in middleware
    
    # Step 1: Check cache
    cache = get_cache()
    cache_key = f"my_stats:{store_id}"
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    # Step 2: Calculate/query
    stats = expensive_calculation()
    
    # Step 3: Cache for 10 minutes
    cache.set(cache_key, stats, ttl=600)
    
    return stats
```

---

## ⚙️ CONFIGURATION

### Environment Variables
```bash
# Redis (optional - defaults to in-memory)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=password  # if needed

# Rate limiting
RATE_LIMIT_RPM=100  # requests per minute per user

# Other
SECRET_KEY=your-jwt-secret
DEBUG=False
```

### Global Configuration (in app.py)
```python
from caching import init_cache, init_rate_limiter

# Initialize caching
init_cache()  # Uses env vars, defaults to in-memory

# Initialize rate limiting
init_rate_limiter()  # Uses RATE_LIMIT_RPM env var
```

---

## 🔍 DEBUGGING TIPS

### Validation Issues
```python
# Check error message
is_valid, error = schema.validate(data)
print(f"Error: {error}")  # Will show specific field that failed
```

### Transaction Issues
```python
# Check transaction result
success, result, error = transaction_operation(...)
if not success:
    print(f"Transaction failed: {error}")
    # Database automatically rolled back
```

### Cache Issues
```python
# Check cache connection
cache = get_cache()
print(f"Cache backend: {type(cache).__name__}")  # InMemoryCache or RedisCache

# Manually clear cache
cache.clear()  # Start fresh
```

### Rate Limiting Issues
```python
# Check if request allowed
limiter = get_rate_limiter()
allowed = limiter.is_allowed("user_123")
print(f"Allowed: {allowed}")

# Check stats
if hasattr(limiter, 'get_user_stats'):
    stats = limiter.get_user_stats("user_123")
    print(f"Requests this minute: {stats}")
```

---

## 📊 PERFORMANCE TIPS

### Caching
- Cache read-heavy endpoints (dashboard, reports)
- Set TTL based on data freshness needs (5-300 seconds typical)
- Invalidate cache on writes (delete key after insert/update)
- Monitor cache hit rate (aim for 80%+)

### Transactions
- Use for multi-step operations only
- Keep transaction time short (<100ms ideal)
- Validate data before transaction (faster failure)
- Monitor transaction rollback rates

### Rate Limiting
- Default 100 req/min is safe for most APIs
- Increase for internal/trusted services
- Monitor for legitimate users hitting limits
- Consider tiered limits (different for different endpoints)

---

## ✅ VERIFICATION CHECKLIST

Before deploying any changes:

- [ ] All inputs validated with appropriate schema
- [ ] Multi-step operations wrapped in transactions
- [ ] Cache invalidated on data modifications
- [ ] Rate limiting doesn't break intended use
- [ ] Error messages are user-friendly
- [ ] Transaction rollbacks tested
- [ ] Cache hit rate is acceptable (80%+)
- [ ] No 500 errors in test runs
- [ ] Response times acceptable (<200ms typical)

---

## 🚨 COMMON MISTAKES

❌ **Don't**: Skip validation
```python
# Bad
item = db.items.insert_one(request.json)
```

✅ **Do**: Validate first
```python
# Good
schema = InventoryItemSchema()
is_valid, error = validate_request(request.json, schema)
if not is_valid:
    return {"error": error}, 400
item = db.items.insert_one(request.json)
```

❌ **Don't**: Forget to invalidate cache
```python
# Bad
db.stats.update_one(...)
return {"success": true}
```

✅ **Do**: Invalidate after write
```python
# Good
db.stats.update_one(...)
cache.delete(f"dashboard_stats:{store_id}")
return {"success": true}
```

❌ **Don't**: Use transactions for single operations
```python
# Bad/Unnecessary
success, result, error = transaction_single_operation(...)
```

✅ **Do**: Use transactions only for multi-step
```python
# Good
success, result, error = transaction_complete_sale(...)  # 5-step operation
```

---

## 📞 SUPPORT RESOURCES

- **Validation Examples**: See PHASE3A_QUICK_REFERENCE.md
- **Transaction Examples**: See PHASE3B_TRANSACTIONS.md
- **Caching Guide**: See caching.py docstrings
- **Complete System**: See PRODUCTION_READY.md

---

**Happy coding! System is production-ready. 🚀**
