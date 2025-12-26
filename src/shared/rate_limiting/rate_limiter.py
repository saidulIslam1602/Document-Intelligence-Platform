"""
Rate Limiting System
Token bucket algorithm for API rate limiting
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Callable, Any
from functools import wraps
from ..config.enhanced_settings import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter
    
    The token bucket algorithm allows bursts while maintaining average rate.
    - Bucket holds tokens (capacity)
    - Tokens are added at a fixed rate
    - Each request consumes a token
    - If no tokens available, request waits
    """
    
    def __init__(
        self,
        name: str,
        rate_per_second: float,
        burst_capacity: Optional[int] = None
    ):
        """
        Initialize rate limiter
        
        Args:
            name: Rate limiter name (for logging)
            rate_per_second: Maximum requests per second
            burst_capacity: Maximum burst size (default: rate_per_second)
        """
        self.name = name
        self.rate_per_second = rate_per_second
        self.burst_capacity = burst_capacity or int(rate_per_second)
        
        # Token bucket state
        self.tokens = float(self.burst_capacity)
        self.last_refill = time.time()
        
        # Statistics
        self.total_requests = 0
        self.total_waited = 0
        self.total_wait_time = 0.0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(
            f"RateLimiter '{name}' initialized: "
            f"rate={rate_per_second}/s, burst={self.burst_capacity}"
        )
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = elapsed * self.rate_per_second
        
        # Add tokens up to capacity
        self.tokens = min(
            self.burst_capacity,
            self.tokens + tokens_to_add
        )
        
        self.last_refill = now
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from bucket (wait if needed)
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Wait time in seconds (0 if no wait)
        """
        async with self._lock:
            self.total_requests += 1
            
            # Refill tokens
            self._refill_tokens()
            
            # Check if we need to wait
            if self.tokens >= tokens:
                # Tokens available, consume immediately
                self.tokens -= tokens
                return 0.0
            else:
                # Not enough tokens, calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate_per_second
                
                # Wait for tokens
                logger.debug(
                    f"RateLimiter '{self.name}': Waiting {wait_time:.2f}s "
                    f"for {tokens} token(s)"
                )
                
                await asyncio.sleep(wait_time)
                
                # Refill and consume
                self._refill_tokens()
                self.tokens -= tokens
                
                # Update statistics
                self.total_waited += 1
                self.total_wait_time += wait_time
                
                return wait_time
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False otherwise
        """
        async with self._lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "name": self.name,
            "rate_per_second": self.rate_per_second,
            "burst_capacity": self.burst_capacity,
            "current_tokens": round(self.tokens, 2),
            "total_requests": self.total_requests,
            "total_waited": self.total_waited,
            "wait_rate": (self.total_waited / self.total_requests * 100)
                if self.total_requests > 0 else 0.0,
            "average_wait_time": (self.total_wait_time / self.total_waited)
                if self.total_waited > 0 else 0.0,
            "total_wait_time": round(self.total_wait_time, 2)
        }
    
    def reset(self):
        """Reset rate limiter to initial state"""
        self.tokens = float(self.burst_capacity)
        self.last_refill = time.time()
        self.total_requests = 0
        self.total_waited = 0
        self.total_wait_time = 0.0
        logger.info(f"RateLimiter '{self.name}': Reset to initial state")


class RateLimiterRegistry:
    """Global registry for rate limiters"""
    
    _limiters: Dict[str, RateLimiter] = {}
    
    @classmethod
    def get(
        cls,
        name: str,
        rate_per_second: Optional[float] = None,
        burst_capacity: Optional[int] = None
    ) -> RateLimiter:
        """Get or create rate limiter"""
        if name not in cls._limiters:
            if rate_per_second is None:
                raise ValueError(f"Rate limiter '{name}' not found and no rate specified")
            cls._limiters[name] = RateLimiter(name, rate_per_second, burst_capacity)
        return cls._limiters[name]
    
    @classmethod
    def get_all(cls) -> Dict[str, RateLimiter]:
        """Get all registered rate limiters"""
        return cls._limiters.copy()
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all rate limiters"""
        return {
            name: limiter.get_stats()
            for name, limiter in cls._limiters.items()
        }
    
    @classmethod
    def reset_all(cls):
        """Reset all rate limiters"""
        for limiter in cls._limiters.values():
            limiter.reset()


def rate_limit(
    name: str,
    rate_per_second: Optional[float] = None,
    burst_capacity: Optional[int] = None,
    tokens: int = 1
):
    """
    Decorator for rate-limited functions
    
    Usage:
        @rate_limit("api_calls", rate_per_second=10, burst_capacity=20)
        async def call_api():
            response = await client.get(url)
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        limiter = RateLimiterRegistry.get(name, rate_per_second, burst_capacity)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Acquire tokens (wait if needed)
            wait_time = await limiter.acquire(tokens)
            
            if wait_time > 0:
                logger.info(
                    f"Rate limited '{name}': Waited {wait_time:.2f}s before {func.__name__}"
                )
            
            # Execute function
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use asyncio.run
            async def _async_acquire():
                return await limiter.acquire(tokens)
            
            wait_time = asyncio.run(_async_acquire())
            
            if wait_time > 0:
                logger.info(
                    f"Rate limited '{name}': Waited {wait_time:.2f}s before {func.__name__}"
                )
            
            return func(*args, **kwargs)
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience function for Form Recognizer rate limiting
def get_form_recognizer_limiter() -> RateLimiter:
    """
    Get Form Recognizer rate limiter
    
    Azure Form Recognizer limits:
    - Free tier: 1 request/second
    - Standard tier: 15 requests/second
    - Custom tier: Configurable
    
    Configuration via environment:
    FORM_RECOGNIZER_RATE_LIMIT_PER_SECOND=10
    FORM_RECOGNIZER_BURST_CAPACITY=20
    """
    settings = get_settings()
    
    return RateLimiterRegistry.get(
        "form_recognizer",
        rate_per_second=settings.form_recognizer.rate_limit_per_second,
        burst_capacity=settings.form_recognizer.burst_capacity
    )


def form_recognizer_rate_limit(func: Callable) -> Callable:
    """
    Rate limit decorator for Form Recognizer calls
    
    Usage:
        @form_recognizer_rate_limit
        async def analyze_invoice(document_url: str):
            result = await form_recognizer.analyze_document(document_url)
            return result
    """
    settings = get_settings()
    
    return rate_limit(
        "form_recognizer",
        rate_per_second=settings.form_recognizer.rate_limit_per_second,
        burst_capacity=settings.form_recognizer.burst_capacity
    )(func)


# Example usage with different services
def openai_rate_limit(func: Callable) -> Callable:
    """Rate limit decorator for OpenAI calls"""
    settings = get_settings()
    
    # OpenAI has different limits per model
    # GPT-4: 500 requests/minute = ~8.3/second
    # GPT-3.5: 3500 requests/minute = ~58/second
    
    return rate_limit(
        "openai",
        rate_per_second=getattr(settings, 'openai_rate_limit_per_second', 8.0),
        burst_capacity=getattr(settings, 'openai_burst_capacity', 20)
    )(func)


def database_rate_limit(func: Callable) -> Callable:
    """Rate limit decorator for database calls"""
    # Useful for preventing database overload
    return rate_limit(
        "database",
        rate_per_second=100.0,  # Conservative limit
        burst_capacity=200
    )(func)

