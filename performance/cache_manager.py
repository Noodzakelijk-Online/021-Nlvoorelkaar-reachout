"""
Multi-Level Cache Manager
Implements L1 (Memory), L2 (SQLite), L3 (Network) caching strategy
for maximum performance while respecting rate limits.
"""

import time
import json
import hashlib
import sqlite3
import threading
from typing import Any, Optional, Dict, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps
import logging
import pickle
import zlib

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0
    size_bytes: int = 0
    compressed: bool = False
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    @property
    def ttl_remaining(self) -> float:
        return max(0, self.expires_at - time.time())


@dataclass
class CacheStats:
    """Cache statistics for monitoring"""
    hits: int = 0
    misses: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LRUCache:
    """
    L1 Memory Cache - Least Recently Used eviction
    
    Features:
    - O(1) get/set operations
    - Automatic size-based eviction
    - TTL support
    - Thread-safe
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                self.stats.misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self.stats.hits += 1
            self.stats.l1_hits += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self._lock:
            ttl = ttl or self.default_ttl
            now = time.time()
            
        # Calculate size
        try:
            size = len(pickle.dumps(value))
        except (pickle.PicklingError, TypeError):
            size = 0
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl,
                size_bytes=size
            )
            
            # Evict if necessary
            while len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            self.stats.total_size_bytes += size
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self.stats.total_size_bytes -= entry.size_bytes
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self.stats.total_size_bytes = 0
    
    def _evict_oldest(self) -> None:
        """Evict least recently used entry"""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self.stats.evictions += 1
            self.stats.total_size_bytes -= entry.size_bytes
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                self.delete(key)
            return len(expired_keys)
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            return not self._cache[key].is_expired


class SQLiteCache:
    """
    L2 Persistent Cache - SQLite-based
    
    Features:
    - Persistent across restarts
    - Compression for large values
    - Automatic cleanup of expired entries
    - Thread-safe
    """
    
    def __init__(self, db_path: str = 'cache.db', default_ttl: int = 86400):
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._local = threading.local()
        self.stats = CacheStats()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        conn = self._get_conn()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                hits INTEGER DEFAULT 0,
                size_bytes INTEGER DEFAULT 0,
                compressed INTEGER DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_cache_expires 
            ON cache(expires_at);
            
            CREATE INDEX IF NOT EXISTS idx_cache_hits 
            ON cache(hits DESC);
        ''')
        conn.commit()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        conn = self._get_conn()
        cursor = conn.execute(
            'SELECT value, expires_at, compressed FROM cache WHERE key = ?',
            (key,)
        )
        row = cursor.fetchone()
        
        if not row:
            self.stats.misses += 1
            return None
        
        # Check expiration
        if time.time() > row['expires_at']:
            self.delete(key)
            self.stats.misses += 1
            return None
        
        # Update hit count
        conn.execute(
            'UPDATE cache SET hits = hits + 1 WHERE key = ?',
            (key,)
        )
        conn.commit()
        
        # Decompress and deserialize
        value_bytes = row['value']
        if row['compressed']:
            value_bytes = zlib.decompress(value_bytes)
        
        try:
            value = pickle.loads(value_bytes)
        except (
            pickle.PickleError,
            pickle.UnpicklingError,
            ValueError,
            TypeError,
            UnicodeDecodeError,
            EOFError
        ):
            value = value_bytes.decode('utf-8')
        
        self.stats.hits += 1
        self.stats.l2_hits += 1
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        now = time.time()
        
        # Serialize value
        try:
            value_bytes = pickle.dumps(value)
        except (pickle.PicklingError, TypeError):
            value_bytes = str(value).encode('utf-8')
        
        # Compress if large
        compressed = 0
        if len(value_bytes) > 1024:  # Compress if > 1KB
            value_bytes = zlib.compress(value_bytes)
            compressed = 1
        
        conn = self._get_conn()
        conn.execute('''
            INSERT OR REPLACE INTO cache 
            (key, value, created_at, expires_at, hits, size_bytes, compressed)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        ''', (key, value_bytes, now, now + ttl, len(value_bytes), compressed))
        conn.commit()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        conn = self._get_conn()
        cursor = conn.execute('DELETE FROM cache WHERE key = ?', (key,))
        conn.commit()
        return cursor.rowcount > 0
    
    def clear(self) -> None:
        """Clear all cache entries"""
        conn = self._get_conn()
        conn.execute('DELETE FROM cache')
        conn.commit()
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        conn = self._get_conn()
        cursor = conn.execute(
            'DELETE FROM cache WHERE expires_at < ?',
            (time.time(),)
        )
        conn.commit()
        return cursor.rowcount
    
    def get_size(self) -> int:
        """Get total cache size in bytes"""
        conn = self._get_conn()
        cursor = conn.execute('SELECT SUM(size_bytes) FROM cache')
        result = cursor.fetchone()[0]
        return result or 0


class MultiLevelCache:
    """
    Multi-Level Cache Manager
    
    Combines L1 (Memory), L2 (SQLite), and L3 (Network) caching
    for optimal performance.
    
    Cache flow:
    1. Check L1 (memory) - instant
    2. Check L2 (SQLite) - fast
    3. Fetch from L3 (network) - slow, rate limited
    4. Populate L1 and L2 with result
    """
    
    # Default TTLs for different data types
    TTL_CONFIG = {
        'volunteer_list': 3600,      # 1 hour
        'volunteer_profile': 21600,  # 6 hours
        'search_results': 1800,      # 30 minutes
        'static_page': 86400,        # 24 hours
        'api_response': 300,         # 5 minutes
        'default': 3600              # 1 hour
    }
    
    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl: int = 300,
        l2_db_path: str = 'cache/cache.db',
        l2_ttl: int = 86400
    ):
        self.l1 = LRUCache(max_size=l1_max_size, default_ttl=l1_ttl)
        self.l2 = SQLiteCache(db_path=l2_db_path, default_ttl=l2_ttl)
        self.stats = CacheStats()
        self._lock = threading.RLock()
        
        # Start background cleanup
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """Start background thread for cache cleanup"""
        def cleanup_loop():
            while True:
                time.sleep(300)  # Every 5 minutes
                try:
                    self.cleanup()
                except sqlite3.DatabaseError as e:
                    logger.error(f"Cache cleanup DB error: {e}")
                except (OSError, RuntimeError) as e:
                    logger.error(f"Cache cleanup runtime error: {e}")
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def get(
        self,
        key: str,
        fetch_func: Optional[Callable[[], Any]] = None,
        data_type: str = 'default'
    ) -> Optional[Any]:
        """
        Get value from cache with automatic fallback
        
        Args:
            key: Cache key
            fetch_func: Function to fetch value if not cached
            data_type: Type of data for TTL configuration
        
        Returns:
            Cached or fetched value, or None
        """
        # Generate cache key hash
        cache_key = self._hash_key(key)
        
        # L1: Check memory cache
        value = self.l1.get(cache_key)
        if value is not None:
            logger.debug(f"L1 cache hit: {key}")
            return value
        
        # L2: Check SQLite cache
        value = self.l2.get(cache_key)
        if value is not None:
            logger.debug(f"L2 cache hit: {key}")
            # Promote to L1
            self.l1.set(cache_key, value, self.TTL_CONFIG.get(data_type, 300))
            return value
        
        # L3: Fetch from network
        if fetch_func:
            logger.debug(f"L3 cache miss, fetching: {key}")
            try:
                value = fetch_func()
                if value is not None:
                    self.set(key, value, data_type)
                    self.stats.l3_hits += 1
                return value
            except (TypeError, OSError, RuntimeError, ValueError) as e:
                logger.error(f"Fetch error for {key}: {e}")
                return None
        
        self.stats.misses += 1
        return None
    
    def set(self, key: str, value: Any, data_type: str = 'default') -> None:
        """
        Set value in both L1 and L2 cache
        
        Args:
            key: Cache key
            value: Value to cache
            data_type: Type of data for TTL configuration
        """
        cache_key = self._hash_key(key)
        ttl = self.TTL_CONFIG.get(data_type, self.TTL_CONFIG['default'])
        
        # Set in both levels
        self.l1.set(cache_key, value, min(ttl, 300))  # L1 max 5 min
        self.l2.set(cache_key, value, ttl)
    
    def delete(self, key: str) -> None:
        """Delete from all cache levels"""
        cache_key = self._hash_key(key)
        self.l1.delete(cache_key)
        self.l2.delete(cache_key)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        # For L1, we need to iterate
        count = 0
        with self.l1._lock:
            keys_to_delete = [
                k for k in self.l1._cache.keys()
                if pattern in k
            ]
            for key in keys_to_delete:
                self.l1.delete(key)
                count += 1
        
        # For L2, use SQL LIKE
        conn = self.l2._get_conn()
        cursor = conn.execute(
            'DELETE FROM cache WHERE key LIKE ?',
            (f'%{pattern}%',)
        )
        conn.commit()
        count += cursor.rowcount
        
        return count
    
    def cleanup(self) -> Dict[str, int]:
        """Clean up expired entries from all levels"""
        l1_cleaned = self.l1.cleanup_expired()
        l2_cleaned = self.l2.cleanup_expired()
        
        return {
            'l1_cleaned': l1_cleaned,
            'l2_cleaned': l2_cleaned,
            'total': l1_cleaned + l2_cleaned
        }
    
    def clear_all(self) -> None:
        """Clear all cache levels"""
        self.l1.clear()
        self.l2.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics"""
        return {
            'l1': {
                'size': len(self.l1),
                'max_size': self.l1.max_size,
                'hits': self.l1.stats.l1_hits,
                'hit_rate': self.l1.stats.hit_rate,
                'memory_bytes': self.l1.stats.total_size_bytes
            },
            'l2': {
                'size_bytes': self.l2.get_size(),
                'hits': self.l2.stats.l2_hits,
                'hit_rate': self.l2.stats.hit_rate
            },
            'total': {
                'hits': self.l1.stats.hits + self.l2.stats.hits,
                'misses': self.l1.stats.misses + self.l2.stats.misses,
                'l3_fetches': self.stats.l3_hits
            }
        }
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Generate consistent hash for cache key"""
        return hashlib.md5(key.encode()).hexdigest()


def cached(
    cache: MultiLevelCache,
    data_type: str = 'default',
    key_func: Optional[Callable[..., str]] = None
):
    """
    Decorator for automatic caching of function results
    
    Usage:
        @cached(cache, data_type='volunteer_profile')
        def get_volunteer(profile_id):
            return fetch_from_network(profile_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            result = cache.get(key, data_type=data_type)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, data_type)
            
            return result
        
        return wrapper
    return decorator


class CacheWarmer:
    """
    Pre-warm cache with frequently accessed data
    """
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self._warming = False
    
    def warm_volunteers(
        self,
        fetch_func: Callable[[int], list],
        pages: int = 10,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """Pre-warm cache with volunteer data"""
        self._warming = True
        count = 0
        
        try:
            for page in range(1, pages + 1):
                if not self._warming:
                    break
                
                key = f"volunteers:page:{page}"
                volunteers = fetch_func(page)
                
                if volunteers:
                    self.cache.set(key, volunteers, 'volunteer_list')
                    count += len(volunteers)
                
                if on_progress:
                    on_progress(page, pages)
                
                time.sleep(1)  # Respect rate limits
        
        finally:
            self._warming = False
        
        return count
    
    def warm_profiles(
        self,
        profile_ids: list,
        fetch_func: Callable[[str], dict],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """Pre-warm cache with volunteer profiles"""
        self._warming = True
        count = 0
        total = len(profile_ids)
        
        try:
            for i, profile_id in enumerate(profile_ids):
                if not self._warming:
                    break
                
                key = f"profile:{profile_id}"
                profile = fetch_func(profile_id)
                
                if profile:
                    self.cache.set(key, profile, 'volunteer_profile')
                    count += 1
                
                if on_progress:
                    on_progress(i + 1, total)
                
                time.sleep(0.5)  # Respect rate limits
        
        finally:
            self._warming = False
        
        return count
    
    def stop(self) -> None:
        """Stop warming process"""
        self._warming = False


# Singleton instance for global access
_cache_instance: Optional[MultiLevelCache] = None


def get_cache() -> MultiLevelCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MultiLevelCache()
    return _cache_instance


def init_cache(
    l1_max_size: int = 1000,
    l2_db_path: str = 'cache/cache.db'
) -> MultiLevelCache:
    """Initialize global cache with custom settings"""
    global _cache_instance
    _cache_instance = MultiLevelCache(
        l1_max_size=l1_max_size,
        l2_db_path=l2_db_path
    )
    return _cache_instance
