"""
MCP Server Rate Limiting
Implements token bucket algorithm for rate limiting MCP tool executions
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Rate limit configurations (per minute unless specified)
RATE_LIMITS = {
    # Global limits
    "global": 1000,  # 1000 requests per minute globally
    
    # Per-user limits
    "user:default": 100,  # 100 requests per minute per user
    "user:admin": 500,  # Admins get higher limits
    "user:ai_agent": 200,  # AI agents get moderate limits
    
    # Per-tool limits (more expensive operations have lower limits)
    "tool:extract_invoice_data": 50,
    "tool:validate_invoice": 100,
    "tool:classify_document": 50,
    "tool:create_fine_tuning_job": 5,  # Very limited - expensive operation
    "tool:get_automation_metrics": 200,
    "tool:process_m365_document": 30,
    "tool:analyze_document_sentiment": 100,
    "tool:extract_document_entities": 100,
    "tool:generate_document_summary": 50,
    "tool:search_documents": 100,
    
    # Resource access limits
    "resource:read": 300,  # 300 resource reads per minute
}

# Time windows (in seconds)
WINDOW_SIZE = 60  # 1 minute


class RateLimiter:
    """Token bucket rate limiter using Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not self._initialized:
            try:
                self.redis_client = redis.from_url(
                    REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                self._initialized = True
                logger.info("Rate limiter initialized with Redis")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis for rate limiting: {e}")
                logger.warning("Rate limiting will use in-memory fallback")
                self.redis_client = None
                self._initialized = True
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int = WINDOW_SIZE
    ) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier for the rate limit (e.g., "user:123", "tool:extract_invoice")
            limit: Maximum number of requests allowed in the window
            window: Time window in seconds
        
        Returns:
            True if within limit, raises HTTPException if exceeded
        """
        if not self._initialized:
            await self.initialize()
        
        # Use Redis-based rate limiting if available
        if self.redis_client:
            return await self._check_rate_limit_redis(key, limit, window)
        else:
            # Fallback to in-memory (not recommended for production)
            return await self._check_rate_limit_memory(key, limit, window)
    
    async def _check_rate_limit_redis(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        """Redis-based rate limiting using sliding window"""
        try:
            redis_key = f"rate_limit:{key}"
            current_time = time.time()
            window_start = current_time - window
            
            # Remove old entries outside the window
            await self.redis_client.zremrangebyscore(redis_key, 0, window_start)
            
            # Count requests in current window
            current_count = await self.redis_client.zcard(redis_key)
            
            if current_count >= limit:
                # Get the oldest request timestamp to calculate retry_after
                oldest = await self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - current_time)
                else:
                    retry_after = window
                
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window": window,
                        "retry_after": retry_after,
                        "key": key
                    },
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Add current request
            await self.redis_client.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiration on the key
            await self.redis_client.expire(redis_key, window + 1)
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # On error, allow the request (fail open)
            return True
    
    # In-memory fallback (simple implementation)
    _memory_store: Dict[str, list] = {}
    
    async def _check_rate_limit_memory(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        """In-memory rate limiting (fallback)"""
        current_time = time.time()
        window_start = current_time - window
        
        # Get or create request list for this key
        if key not in self._memory_store:
            self._memory_store[key] = []
        
        # Remove old requests
        self._memory_store[key] = [
            t for t in self._memory_store[key] if t > window_start
        ]
        
        # Check limit
        if len(self._memory_store[key]) >= limit:
            oldest_time = min(self._memory_store[key])
            retry_after = int(oldest_time + window - current_time)
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": window,
                    "retry_after": retry_after,
                    "key": key
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add current request
        self._memory_store[key].append(current_time)
        
        return True
    
    async def check_multiple_limits(
        self,
        limits: Dict[str, int],
        window: int = WINDOW_SIZE
    ) -> bool:
        """
        Check multiple rate limits at once
        
        Args:
            limits: Dictionary of {key: limit} pairs
            window: Time window in seconds
        
        Returns:
            True if all limits are satisfied
        """
        for key, limit in limits.items():
            await self.check_rate_limit(key, limit, window)
        return True
    
    async def get_remaining(self, key: str, limit: int, window: int = WINDOW_SIZE) -> int:
        """Get remaining requests in current window"""
        if not self._initialized:
            await self.initialize()
        
        try:
            if self.redis_client:
                redis_key = f"rate_limit:{key}"
                current_time = time.time()
                window_start = current_time - window
                
                # Clean old entries
                await self.redis_client.zremrangebyscore(redis_key, 0, window_start)
                
                # Count current requests
                current_count = await self.redis_client.zcard(redis_key)
                
                return max(0, limit - current_count)
            else:
                # Memory fallback
                current_time = time.time()
                window_start = current_time - window
                
                if key not in self._memory_store:
                    return limit
                
                # Clean old entries
                self._memory_store[key] = [
                    t for t in self._memory_store[key] if t > window_start
                ]
                
                return max(0, limit - len(self._memory_store[key]))
                
        except Exception as e:
            logger.error(f"Failed to get remaining requests: {e}")
            return limit  # Return full limit on error


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_mcp_rate_limits(
    request: Request,
    user_id: str,
    user_role: str,
    operation_type: str,  # "tool" or "resource"
    operation_name: Optional[str] = None
) -> bool:
    """
    Check all applicable rate limits for an MCP operation
    
    Args:
        request: FastAPI request object
        user_id: User ID making the request
        user_role: User role (admin, developer, etc.)
        operation_type: Type of operation ("tool" or "resource")
        operation_name: Specific tool or resource name
    
    Returns:
        True if all rate limits pass
    
    Raises:
        HTTPException: If any rate limit is exceeded
    """
    limits_to_check = {}
    
    # 1. Global rate limit
    limits_to_check["global"] = RATE_LIMITS["global"]
    
    # 2. Per-user rate limit (based on role)
    user_limit_key = f"user:{user_role}" if f"user:{user_role}" in RATE_LIMITS else "user:default"
    limits_to_check[f"user:{user_id}"] = RATE_LIMITS[user_limit_key]
    
    # 3. Per-operation rate limit
    if operation_type == "tool" and operation_name:
        tool_key = f"tool:{operation_name}"
        if tool_key in RATE_LIMITS:
            limits_to_check[tool_key] = RATE_LIMITS[tool_key]
            # Also add per-user-per-tool limit
            limits_to_check[f"user:{user_id}:tool:{operation_name}"] = RATE_LIMITS[tool_key]
    
    elif operation_type == "resource":
        limits_to_check["resource:read"] = RATE_LIMITS["resource:read"]
        limits_to_check[f"user:{user_id}:resource:read"] = RATE_LIMITS["resource:read"]
    
    # Check all limits
    await rate_limiter.check_multiple_limits(limits_to_check)
    
    return True


async def get_rate_limit_info(user_id: str, user_role: str) -> Dict[str, Any]:
    """
    Get rate limit information for a user
    
    Returns:
        Dictionary with rate limit info and remaining requests
    """
    user_limit_key = f"user:{user_role}" if f"user:{user_role}" in RATE_LIMITS else "user:default"
    user_limit = RATE_LIMITS[user_limit_key]
    
    remaining = await rate_limiter.get_remaining(f"user:{user_id}", user_limit)
    
    return {
        "user_id": user_id,
        "role": user_role,
        "rate_limit": {
            "requests_per_minute": user_limit,
            "remaining": remaining,
            "window_seconds": WINDOW_SIZE
        },
        "tool_limits": {
            tool.replace("tool:", ""): limit
            for tool, limit in RATE_LIMITS.items()
            if tool.startswith("tool:")
        }
    }


# Middleware for rate limiting
class RateLimitMiddleware:
    """Middleware to add rate limit headers to responses"""
    
    @staticmethod
    async def add_rate_limit_headers(
        request: Request,
        response,
        user_id: str,
        user_role: str
    ):
        """Add rate limit headers to response"""
        try:
            user_limit_key = f"user:{user_role}" if f"user:{user_role}" in RATE_LIMITS else "user:default"
            user_limit = RATE_LIMITS[user_limit_key]
            
            remaining = await rate_limiter.get_remaining(f"user:{user_id}", user_limit)
            
            response.headers["X-RateLimit-Limit"] = str(user_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Window"] = str(WINDOW_SIZE)
            
        except Exception as e:
            logger.error(f"Failed to add rate limit headers: {e}")
        
        return response


if __name__ == "__main__":
    # Test rate limiter
    import asyncio
    
    async def test_rate_limiter():
        limiter = RateLimiter()
        await limiter.initialize()
        
        print("Testing rate limiter...")
        
        # Test basic rate limit
        test_key = "test_user:123"
        test_limit = 5
        
        print(f"\nTesting with limit of {test_limit} requests:")
        
        for i in range(test_limit + 2):
            try:
                await limiter.check_rate_limit(test_key, test_limit, window=60)
                remaining = await limiter.get_remaining(test_key, test_limit, window=60)
                print(f"Request {i+1}: ✓ Allowed (remaining: {remaining})")
            except HTTPException as e:
                print(f"Request {i+1}: ✗ Blocked - {e.detail['error']}")
                print(f"  Retry after: {e.detail['retry_after']} seconds")
        
        print("\nRate limiter test complete!")
    
    asyncio.run(test_rate_limiter())

