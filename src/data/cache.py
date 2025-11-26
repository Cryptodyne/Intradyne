from collections import OrderedDict
import time
from typing import Any, Optional, Dict
import hashlib
import json

class EnhancedCache:
    """
    Enhanced caching system with LRU eviction, TTL, and statistics tracking.
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 60):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self._cache = OrderedDict()
        self._timestamps = {}
        self._ttls = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'sets': 0
        }
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        key_str = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            ttl: Time-to-live override (optional)
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._stats['misses'] += 1
            return None
        
        # Check if expired
        age = time.time() - self._timestamps[key]
        item_ttl = self._ttls.get(key, self._default_ttl)
        
        if age > item_ttl:
            # Expired
            self._stats['expirations'] += 1
            self._stats['misses'] += 1
            del self._cache[key]
            del self._timestamps[key]
            del self._ttls[key]
            return None
        
        # Cache hit - move to end (most recently used)
        self._cache.move_to_end(key)
        self._stats['hits'] += 1
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live override (optional)
        """
        # Check if we need to evict
        if key not in self._cache and len(self._cache) >= self._max_size:
            # Evict least recently used (first item)
            evicted_key = next(iter(self._cache))
            del self._cache[evicted_key]
            del self._timestamps[evicted_key]
            del self._ttls[evicted_key]
            self._stats['evictions'] += 1
        
        # Set value
        self._cache[key] = value
        self._timestamps[key] = time.time()
        self._ttls[key] = ttl if ttl is not None else self._default_ttl
        self._stats['sets'] += 1
        
        # Move to end (most recently used)
        if key in self._cache:
            self._cache.move_to_end(key)
    
    def invalidate(self, key: str):
        """Remove a specific key from cache."""
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            del self._ttls[key]
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
        self._ttls.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': hit_rate,
            'evictions': self._stats['evictions'],
            'expirations': self._stats['expirations'],
            'sets': self._stats['sets'],
            'size': len(self._cache),
            'max_size': self._max_size
        }
    
    def warm_up(self, keys_values: Dict[str, Any], ttl: Optional[int] = None):
        """
        Pre-populate cache with multiple values.
        
        Args:
            keys_values: Dictionary of key-value pairs
            ttl: Time-to-live for all values
        """
        for key, value in keys_values.items():
            self.set(key, value, ttl)
    
    def get_size_bytes(self) -> int:
        """
        Estimate cache size in bytes (rough approximation).
        
        Returns:
            Estimated size in bytes
        """
        import sys
        total_size = 0
        for key, value in self._cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(value)
        return total_size
    
    def __len__(self) -> int:
        """Return number of items in cache."""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None
