"""
Redis Caching Service
High-performance caching for improved API response times
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from ..config.settings import config_manager

class RedisCacheService:
    """High-performance Redis caching service"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour default TTL
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            # Get Redis configuration from environment variables
            redis_host = os.getenv('REDIS_HOST', 'redis')  # Default to 'redis' for Docker
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_db = int(os.getenv('REDIS_DB', '0'))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis cache service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis cache: {str(e)}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cache key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            result = await self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            return await self.redis_client.exists(key) > 0
            
        except Exception as e:
            self.logger.error(f"Error checking cache key {key}: {str(e)}")
            return False
    
    async def get_or_set(self, key: str, fetch_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or fetch and set"""
        try:
            # Try to get from cache first
            cached_value = await self.get(key)
            if cached_value is not None:
                return cached_value
            
            # Fetch from source
            value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
            
            # Set in cache
            await self.set(key, value, ttl)
            return value
            
        except Exception as e:
            self.logger.error(f"Error in get_or_set for key {key}: {str(e)}")
            # Fallback to direct fetch
            return await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            self.logger.error(f"Error invalidating pattern {pattern}: {str(e)}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}

# Cache decorators
def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Cache result
            await cache_service.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def cache_invalidate(pattern: str):
    """Decorator to invalidate cache on function execution"""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Invalidate cache
            await cache_service.invalidate_pattern(pattern)
            return result
        
        return wrapper
    return decorator

# Global cache service instance
cache_service = RedisCacheService()

# Common cache keys
class CacheKeys:
    """Common cache key patterns"""
    USER_DOCUMENTS = "user_documents:{user_id}"
    DOCUMENT_METADATA = "document_metadata:{document_id}"
    ANALYTICS_METRICS = "analytics_metrics:{time_range}"
    CONVERSATION_HISTORY = "conversation_history:{conversation_id}"
    USER_CONVERSATIONS = "user_conversations:{user_id}"
    SYSTEM_HEALTH = "system_health"
    PROCESSING_JOBS = "processing_jobs:{user_id}"