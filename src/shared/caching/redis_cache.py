"""
Production-grade Redis caching layer for performance optimization
Reduces database queries and API calls, improves response times
"""

import json
import asyncio
import logging
from typing import Optional, Any, Callable
from functools import wraps
import hashlib
import redis.asyncio as aioredis
from datetime import timedelta

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Enterprise Redis caching with connection pooling and error handling
    
    Features:
    - Async/await support for non-blocking operations
    - Connection pooling for resource efficiency
    - Automatic serialization/deserialization
    - TTL (Time To Live) management
    - Cache invalidation patterns
    - Error resilience (fails gracefully)
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_connections: int = 50,
        default_ttl: int = 300,  # 5 minutes
    ):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.default_ttl = default_ttl
        self._pool = None
        self._client = None
    
    async def connect(self):
        """Initialize Redis connection pool"""
        try:
            self._pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self._client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            await self._pool.disconnect()
            logger.info("Redis cache disconnected")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_parts = [str(prefix)]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        key_string = ":".join(key_parts)
        
        # Hash long keys to keep them short
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return key_string
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache GET error for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with TTL"""
        if not self._client:
            return False
        
        try:
            serialized = json.dumps(value)
            ttl_seconds = ttl or self.default_ttl
            await self._client.setex(key, ttl_seconds, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache SET error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._client:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE error for {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._client:
            return 0
        
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache DELETE_PATTERN error for {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client:
            return False
        
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache EXISTS error for {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter (for rate limiting, metrics)"""
        if not self._client:
            return None
        
        try:
            return await self._client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache INCREMENT error for {key}: {e}")
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key"""
        if not self._client:
            return False
        
        try:
            return await self._client.expire(key, ttl)
        except Exception as e:
            logger.warning(f"Cache EXPIRE error for {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key"""
        if not self._client:
            return None
        
        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.warning(f"Cache TTL error for {key}: {e}")
            return None
    
    def cache_result(
        self,
        prefix: str,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable] = None,
    ):
        """
        Decorator to cache function results
        
        Usage:
            @cache.cache_result("documents", ttl=300)
            async def get_document(doc_id: str):
                return await db.get_document(doc_id)
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = self._generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_value
                
                # Cache miss - execute function
                logger.debug(f"Cache MISS: {cache_key}")
                result = await func(*args, **kwargs)
                
                # Store in cache
                if result is not None:
                    await self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator


# Global cache instance
cache = RedisCache()


async def init_cache(redis_url: str = "redis://localhost:6379"):
    """Initialize global cache"""
    global cache
    cache = RedisCache(redis_url=redis_url)
    await cache.connect()
    return cache


async def close_cache():
    """Close global cache"""
    if cache:
        await cache.disconnect()


# Utility functions for common cache patterns

async def cache_get_or_set(
    key: str,
    fetch_func: Callable,
    ttl: int = 300,
) -> Any:
    """Get from cache or fetch and set"""
    value = await cache.get(key)
    if value is not None:
        return value
    
    value = await fetch_func()
    if value is not None:
        await cache.set(key, value, ttl)
    
    return value


async def invalidate_user_cache(user_id: str):
    """Invalidate all caches for a user"""
    pattern = f"*:user:{user_id}:*"
    count = await cache.delete_pattern(pattern)
    logger.info(f"Invalidated {count} cache entries for user {user_id}")


async def invalidate_document_cache(document_id: str):
    """Invalidate all caches for a document"""
    patterns = [
        f"document:{document_id}:*",
        f"*:doc:{document_id}:*",
    ]
    
    total = 0
    for pattern in patterns:
        count = await cache.delete_pattern(pattern)
        total += count
    
    logger.info(f"Invalidated {total} cache entries for document {document_id}")


# Cache warming functions for frequently accessed data
async def warm_cache_for_user(user_id: str):
    """Pre-load frequently accessed user data into cache"""
    logger.info(f"Warming cache for user {user_id}")
    # Implement based on your data access patterns
    pass

