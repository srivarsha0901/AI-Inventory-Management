"""
Redis caching layer and batch processing utilities.
Provides key-value caching with TTL and automatic invalidation.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import json
import hashlib


class InMemoryCache:
    """
    In-memory cache (fallback when Redis unavailable).
    Used for development/testing without Redis.
    """
    
    def __init__(self):
        self.store = {}
        self.expiry = {}
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if key in self.expiry:
            if datetime.now() > self.expiry[key]:
                del self.store[key]
                del self.expiry[key]
                return None
        return self.store.get(key)
    
    def set(self, key: str, value: str, ttl_seconds: int = 1800):
        """Set value with TTL (seconds)."""
        self.store[key] = value
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def delete(self, key: str):
        """Delete key from cache."""
        self.store.pop(key, None)
        self.expiry.pop(key, None)
    
    def clear_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        prefix = pattern.replace("*", "")
        keys_to_delete = [k for k in self.store.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            self.delete(key)


class CacheManager:
    """
    Unified cache interface supporting both Redis and in-memory fallback.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Redis client (optional). If None, uses in-memory cache.
        """
        self.redis = redis_client
        self.memory_cache = InMemoryCache()
        self.use_redis = redis_client is not None
    
    def get(self, key: str) -> Optional[Dict]:
        """Get value from cache (with auto JSON parsing)."""
        try:
            if self.use_redis:
                value = self.redis.get(key)
            else:
                value = self.memory_cache.get(key)
            
            if not value:
                return None
            
            # Try parsing as JSON
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            return json.loads(value)
        except Exception:
            return None
    
    def set(self, key: str, value: Dict, ttl_minutes: int = 30):
        """Set value in cache (with JSON serialization)."""
        try:
            json_value = json.dumps(value, default=str)  # default=str for datetime
            ttl_seconds = ttl_minutes * 60
            
            if self.use_redis:
                self.redis.setex(key, ttl_seconds, json_value)
            else:
                self.memory_cache.set(key, json_value, ttl_seconds)
        except Exception as e:
            # Silently fail - cache is optional
            print(f"Cache set failed: {e}")
    
    def delete(self, key: str):
        """Delete key from cache."""
        try:
            if self.use_redis:
                self.redis.delete(key)
            else:
                self.memory_cache.delete(key)
        except Exception:
            pass
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern (e.g., 'inventory:*')."""
        try:
            if self.use_redis:
                # Redis: scan for matching keys
                cursor = 0
                while True:
                    cursor, keys = self.redis.scan(cursor, match=pattern)
                    if keys:
                        self.redis.delete(*keys)
                    if cursor == 0:
                        break
            else:
                self.memory_cache.clear_pattern(pattern)
        except Exception:
            pass
    
    def cached(self, ttl_minutes: int = 30):
        """
        Decorator for caching function results.
        
        Usage:
            @cache.cached(ttl_minutes=30)
            def get_dashboard_stats(store_id):
                # Expensive query
                return stats
        """
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # Generate cache key from function name + args
                cache_key = f"{func.__name__}:{hashlib.md5(str((args, kwargs)).encode()).hexdigest()}"
                
                # Try cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Cache miss - execute function
                result = func(*args, **kwargs)
                self.set(cache_key, result or {}, ttl_minutes)
                return result
            
            return wrapper
        return decorator


# ✅ BATCH PROCESSING UTILITIES

class BatchProcessor:
    """Processes large datasets in batches with progress tracking."""
    
    def __init__(self, batch_size: int = 500):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items per batch
        """
        self.batch_size = batch_size
    
    def process_items(self, items: List[Dict], 
                     process_func: Callable,
                     progress_callback: Optional[Callable] = None) -> Dict:
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            process_func: Function to call for each batch
            progress_callback: Optional callback for progress updates
        
        Returns:
            {"total": N, "processed": M, "errors": E, "results": [...]}
        """
        total = len(items)
        processed = 0
        errors = 0
        results = []
        failed_items = []
        
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            
            try:
                # Process batch
                batch_result = process_func(batch)
                results.extend(batch_result or [])
                processed += len(batch)
            except Exception as e:
                # Track failed batch
                errors += len(batch)
                failed_items.append({
                    "batch_index": i // self.batch_size,
                    "start": i,
                    "end": min(i + self.batch_size, total),
                    "error": str(e)
                })
            
            # Progress callback
            if progress_callback:
                progress_callback({
                    "processed": processed,
                    "total": total,
                    "percent": round((processed / total) * 100, 1),
                    "errors": errors
                })
        
        return {
            "total": total,
            "processed": processed,
            "errors": errors,
            "success_rate": round((processed / total) * 100, 1) if total > 0 else 0,
            "results": results,
            "failed_items": failed_items
        }


# ✅ RATE LIMITING UTILITIES

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_minute: int = 100):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Rate limit (requests/minute)
        """
        self.rate = requests_per_minute
        self.buckets = {}  # user_id -> {"tokens": N, "last_refill": datetime}
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed for user."""
        now = datetime.now()
        
        if user_id not in self.buckets:
            # New user - initialize bucket
            self.buckets[user_id] = {
                "tokens": self.rate,
                "last_refill": now
            }
            return True
        
        bucket = self.buckets[user_id]
        
        # Refill tokens based on time elapsed
        elapsed = (now - bucket["last_refill"]).total_seconds()
        refill_rate = self.rate / 60  # tokens per second
        tokens_to_add = elapsed * refill_rate
        
        bucket["tokens"] = min(self.rate, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now
        
        # Check if request allowed
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False
    
    def get_retry_after(self, user_id: str) -> int:
        """Get seconds to wait before next request is allowed."""
        if user_id not in self.buckets:
            return 0
        
        bucket = self.buckets[user_id]
        refill_rate = self.rate / 60
        wait_time = (1 - bucket["tokens"]) / refill_rate
        return max(0, int(wait_time))


# ✅ CSV BATCH IMPORT

def batch_import_csv(db, store_id, csv_rows: List[Dict], 
                    progress_callback: Optional[Callable] = None) -> Dict:
    """
    Import CSV rows in batches with transaction support.
    
    Args:
        db: MongoDB connection
        store_id: Store ID for imports
        csv_rows: List of row dicts from CSV
        progress_callback: Callback for progress updates
    
    Returns:
        {"total": N, "created": C, "updated": U, "errors": E}
    """
    from transactions import TransactionManager, transaction_onboard_inventory
    from bson import ObjectId
    
    processor = BatchProcessor(batch_size=500)
    tx_manager = TransactionManager(db.client)
    
    def process_batch(batch_items):
        """Process one batch with transaction."""
        # Convert CSV rows to inventory format
        inventory_items = []
        for row in batch_items:
            try:
                inventory_items.append({
                    "name": row.get("name", ""),
                    "category": row.get("category", "General"),
                    "unit": row.get("unit", "units"),
                    "cost_price": float(row.get("cost_price", 0)),
                    "selling_price": float(row.get("selling_price", 0)),
                    "stock": int(row.get("stock", 0)),
                    "safety_stock": int(row.get("safety_stock", 10)),
                    "shelf_life_days": int(row.get("shelf_life_days", 0)),
                    "restock_days": int(row.get("restock_days", 7)),
                    "emoji": row.get("emoji", "📦"),
                })
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid row format: {e}")
        
        # Execute transaction
        try:
            store_id_obj = ObjectId(store_id) if isinstance(store_id, str) else store_id
        except:
            store_id_obj = store_id
        
        success, result, error = tx_manager.execute_transaction(
            transaction_onboard_inventory,
            db=db,
            store_id=store_id_obj,
            items=inventory_items
        )
        
        if not success:
            raise Exception(f"Transaction failed: {error}")
        
        return [result]  # Return result wrapped in list for batch processor
    
    # Process batches
    return processor.process_items(csv_rows, process_batch, progress_callback)


# ✅ GLOBAL CACHE & RATE LIMIT INSTANCES

_cache_manager = None
_rate_limiter = None


def init_cache(redis_client=None):
    """Initialize global cache manager."""
    global _cache_manager
    _cache_manager = CacheManager(redis_client)


def init_rate_limiter(requests_per_minute: int = 100):
    """Initialize global rate limiter."""
    global _rate_limiter
    _rate_limiter = RateLimiter(requests_per_minute)


def get_cache() -> CacheManager:
    """Get global cache manager."""
    global _cache_manager
    if _cache_manager is None:
        init_cache()  # Initialize with in-memory cache
    return _cache_manager


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        init_rate_limiter()
    return _rate_limiter
