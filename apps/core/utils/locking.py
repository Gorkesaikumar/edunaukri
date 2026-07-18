import logging
from functools import wraps
from django.core.cache import cache

logger = logging.getLogger(__name__)

def redis_lock(lock_id, timeout=300):
    """
    Decorator to ensure that a task is not executed concurrently.
    Uses Django's caching framework (which should be backed by Redis).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"lock:{lock_id}"
            
            # cache.add returns True if it added the key, False if it already existed
            acquired = cache.add(cache_key, "true", timeout)
            
            if not acquired:
                logger.info(f"Could not acquire lock for {lock_id}. Task skipped.")
                return None
                
            try:
                return func(*args, **kwargs)
            finally:
                cache.delete(cache_key)
                
        return wrapper
    return decorator
