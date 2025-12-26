"""
Rate Limiting System - Token Bucket Algorithm Implementation

This module implements the Token Bucket algorithm for API rate limiting, which provides
a flexible approach to controlling request rates while allowing burst traffic.

Algorithm Overview:
------------------
The Token Bucket algorithm works like a bucket that holds tokens:
1. The bucket has a maximum capacity (burst_capacity)
2. Tokens are added to the bucket at a fixed rate (rate_per_second)
3. Each request consumes one or more tokens
4. If tokens are available, the request proceeds immediately
5. If no tokens available, the request waits until tokens are refilled

Benefits:
---------
- Allows burst traffic (up to burst_capacity)
- Smooth rate limiting over time
- Prevents thundering herd problems
- Protects downstream services from overload
- Fair queuing of requests

Use Cases:
----------
- Azure Form Recognizer API rate limiting (15 req/sec standard tier)
- OpenAI API rate limiting (varies by model and tier)
- Database connection pool management
- External API calls with quota limits
- Preventing DDoS and abuse

Example:
--------
    # Basic usage with decorator
    @rate_limit("my_api", rate_per_second=10, burst_capacity=20)
    async def call_external_api():
        response = await client.get("https://api.example.com")
        return response.json()

    # Programmatic usage
    limiter = RateLimiterRegistry.get("my_api", rate_per_second=10)
    await limiter.acquire(tokens=1)
    result = await expensive_operation()

References:
-----------
- Token Bucket Algorithm: https://en.wikipedia.org/wiki/Token_bucket
- Leaky Bucket vs Token Bucket: https://www.wikiwand.com/en/Leaky_bucket
- Rate Limiting Patterns: https://cloud.google.com/architecture/rate-limiting-strategies

Author: Document Intelligence Platform Team
Version: 2.0.0
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
    Token Bucket Rate Limiter Implementation
    
    This class implements a thread-safe, async-friendly token bucket rate limiter
    that prevents exceeding specified rate limits while allowing burst traffic.
    
    How It Works:
    -------------
    1. Initialize with a rate (tokens/second) and burst capacity
    2. Tokens are added continuously at the specified rate
    3. Each request consumes tokens from the bucket
    4. If tokens available: request proceeds immediately
    5. If no tokens: request waits until tokens are available
    
    Mathematical Model:
    -------------------
    tokens(t) = min(burst_capacity, tokens(t-1) + rate * elapsed_time)
    wait_time = (tokens_needed - current_tokens) / rate_per_second
    
    Thread Safety:
    --------------
    Uses asyncio.Lock to ensure thread-safe token management in concurrent environments.
    
    Performance:
    ------------
    - Time complexity: O(1) for token acquisition
    - Space complexity: O(1) per rate limiter
    - Memory usage: ~1KB per limiter instance
    
    Example:
    --------
        # Create a rate limiter for 10 req/sec with 20 burst capacity
        limiter = RateLimiter("api_calls", rate_per_second=10, burst_capacity=20)
        
        # Acquire tokens (waits if needed)
        wait_time = await limiter.acquire(tokens=1)
        
        # Try to acquire without waiting
        if await limiter.try_acquire(tokens=1):
            await call_api()
        
        # Get statistics
        stats = limiter.get_stats()
        print(f"Wait rate: {stats['wait_rate']}%")
    
    Attributes:
        name (str): Identifier for logging and monitoring
        rate_per_second (float): Token refill rate
        burst_capacity (int): Maximum tokens in bucket
        tokens (float): Current available tokens
        last_refill (float): Timestamp of last token refill
        total_requests (int): Total requests processed
        total_waited (int): Number of requests that had to wait
        total_wait_time (float): Cumulative wait time in seconds
    
    Note:
        Suitable for rate limiting external APIs, protecting downstream services,
        and managing resource consumption. Not suitable for hard real-time systems
        where microsecond precision is required.
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
        """
        Refill tokens based on elapsed time since last refill.
        
        This method implements the core token bucket refill logic:
        1. Calculate time elapsed since last refill
        2. Calculate tokens to add: elapsed_time * rate_per_second
        3. Add tokens but never exceed burst_capacity (bucket overflow protection)
        4. Update last_refill timestamp
        
        Algorithm:
        ----------
        tokens_new = min(burst_capacity, tokens_old + (time_elapsed * rate))
        
        Example:
        --------
        If rate=10/sec and 0.5 seconds elapsed:
        - tokens_to_add = 0.5 * 10 = 5 tokens
        - If current tokens = 15 and capacity = 20:
          new tokens = min(20, 15 + 5) = 20 (capped at capacity)
        
        Performance:
        ------------
        - Constant time operation: O(1)
        - Called on every acquire() to ensure accurate token count
        
        Note:
            This is an internal method called automatically by acquire() and try_acquire().
            It maintains the mathematical invariant that tokens never exceed capacity.
        """
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add based on elapsed time
        # Formula: tokens = elapsed_seconds * tokens_per_second
        tokens_to_add = elapsed * self.rate_per_second
        
        # Add tokens up to capacity (prevent bucket overflow)
        # This ensures we never exceed the maximum burst capacity
        self.tokens = min(
            self.burst_capacity,
            self.tokens + tokens_to_add
        )
        
        # Update timestamp for next refill calculation
        self.last_refill = now
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from bucket, waiting if necessary to maintain rate limit.
        
        This is the primary method for rate limiting. It guarantees that requests
        will not exceed the configured rate, by blocking (asynchronously) when
        tokens are unavailable.
        
        Behavior:
        ---------
        1. Acquire lock for thread safety
        2. Refill tokens based on elapsed time
        3. If enough tokens available: consume and return immediately
        4. If insufficient tokens: calculate wait time and sleep
        5. After waiting: consume tokens and return wait time
        
        Wait Time Calculation:
        ----------------------
        wait_time = (tokens_needed - current_tokens) / rate_per_second
        
        Example:
        --------
        If rate=10/sec, current tokens=2, and need 5 tokens:
        wait_time = (5 - 2) / 10 = 0.3 seconds
        
        Thread Safety:
        --------------
        Uses asyncio.Lock to ensure atomic token consumption across
        concurrent coroutines. This prevents race conditions where
        multiple requests might consume the same tokens.
        
        Args:
            tokens (int, optional): Number of tokens to acquire. Defaults to 1.
                For operations with variable cost, pass the cost in tokens.
                Example: Large API request might cost 5 tokens.
        
        Returns:
            float: Actual wait time in seconds. Returns 0.0 if no wait required.
                This can be used for monitoring and alerting on rate limit pressure.
        
        Raises:
            ValueError: If tokens <= 0 (invalid request)
        
        Example:
        --------
            # Basic usage - acquire 1 token
            wait_time = await limiter.acquire()
            if wait_time > 0:
                logger.warning(f"Rate limited for {wait_time:.2f}s")
            
            # Acquire multiple tokens for expensive operation
            wait_time = await limiter.acquire(tokens=5)
            await expensive_api_call()
            
            # Monitor rate limit pressure
            wait_time = await limiter.acquire()
            if wait_time > 1.0:
                alert("Rate limit pressure high")
        
        Performance Notes:
        ------------------
        - O(1) time complexity
        - Async-friendly (doesn't block event loop during wait)
        - Statistics are tracked for monitoring
        
        Monitoring:
        -----------
        Track these metrics for operational insights:
        - total_waited: Number of requests that had to wait
        - wait_rate: Percentage of requests delayed
        - average_wait_time: Average delay per waiting request
        
        See Also:
            try_acquire(): Non-blocking variant that returns False instead of waiting
        """
        async with self._lock:
            # Track total requests for statistics
            self.total_requests += 1
            
            # Refill tokens based on elapsed time
            self._refill_tokens()
            
            # Fast path: tokens available, consume immediately
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Slow path: insufficient tokens, must wait
            else:
                # Calculate tokens needed after current ones are used
                tokens_needed = tokens - self.tokens
                
                # Calculate wait time using rate
                # Formula: time = tokens / rate
                wait_time = tokens_needed / self.rate_per_second
                
                # Log rate limiting event for monitoring
                logger.debug(
                    f"RateLimiter '{self.name}': Waiting {wait_time:.2f}s "
                    f"for {tokens} token(s). Current tokens: {self.tokens:.2f}"
                )
                
                # Asynchronously wait for tokens to be available
                # This yields control back to event loop
                await asyncio.sleep(wait_time)
                
                # After waiting, refill tokens and consume
                self._refill_tokens()
                self.tokens -= tokens
                
                # Update wait statistics for monitoring
                self.total_waited += 1
                self.total_wait_time += wait_time
                
                return wait_time
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens without waiting (non-blocking variant).
        
        This method provides a non-blocking alternative to acquire(). It's useful
        when you want to fail fast rather than wait for rate limits.
        
        Use Cases:
        ----------
        - Best-effort operations that can be skipped if rate limited
        - Circuit breaker patterns (fail fast when overloaded)
        - Adaptive algorithms that adjust based on available capacity
        - Load shedding during high traffic periods
        
        Behavior:
        ---------
        1. Acquire lock for thread safety
        2. Refill tokens based on elapsed time
        3. If enough tokens: consume and return True
        4. If insufficient tokens: return False immediately (no wait)
        
        Args:
            tokens (int, optional): Number of tokens to acquire. Defaults to 1.
        
        Returns:
            bool: True if tokens were acquired, False if insufficient tokens.
                If False, the caller should handle the rate limit (e.g., skip operation,
                queue for later, return cached result, or return error).
        
        Example:
        --------
            # Best-effort cache refresh
            if await limiter.try_acquire():
                await refresh_cache()
            else:
                logger.debug("Rate limited, skipping cache refresh")
                return cached_value
            
            # Adaptive retry strategy
            for attempt in range(max_retries):
                if await limiter.try_acquire():
                    return await api_call()
                await asyncio.sleep(backoff_time)
            raise RateLimitError("Exceeded retry limit")
            
            # Load shedding
            if not await limiter.try_acquire():
                return {"error": "Service unavailable", "retry_after": 1.0}
        
        Performance Notes:
        ------------------
        - O(1) time complexity
        - No blocking or waiting
        - Returns immediately
        
        See Also:
            acquire(): Blocking variant that waits for tokens
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            self._refill_tokens()
            
            # Check if sufficient tokens available
            if self.tokens >= tokens:
                # Tokens available - consume and succeed
                self.tokens -= tokens
                return True
            else:
                # Insufficient tokens - fail fast without waiting
                return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for monitoring and alerting.
        
        This method provides operational metrics useful for:
        - Monitoring rate limit pressure
        - Capacity planning
        - Alerting on excessive wait times
        - Understanding usage patterns
        - Tuning rate limits
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - name (str): Rate limiter identifier
                - rate_per_second (float): Configured token refill rate
                - burst_capacity (int): Maximum tokens in bucket
                - current_tokens (float): Currently available tokens
                - total_requests (int): Total requests processed
                - total_waited (int): Number of requests that had to wait
                - wait_rate (float): Percentage of requests delayed (0-100)
                - average_wait_time (float): Average delay per waiting request (seconds)
                - total_wait_time (float): Cumulative wait time (seconds)
        
        Metrics Guide:
        --------------
        - wait_rate > 50%: Consider increasing rate limit or capacity
        - average_wait_time > 1s: Users experiencing noticeable delays
        - current_tokens near 0: High sustained load
        - total_waited increasing rapidly: Potential capacity issue
        
        Example:
        --------
            stats = limiter.get_stats()
            
            # Alert on high wait rate
            if stats['wait_rate'] > 50:
                alert("High rate limit pressure", stats)
            
            # Monitor current capacity
            if stats['current_tokens'] < 1:
                logger.warning("Rate limiter near capacity")
            
            # Expose to Prometheus
            rate_limit_wait_rate.labels(name=stats['name']).set(stats['wait_rate'])
        
        Use with Monitoring:
        --------------------
            # Expose metrics to Prometheus
            from prometheus_client import Gauge
            
            wait_rate = Gauge('rate_limit_wait_rate', 'Rate limit wait percentage')
            wait_time = Gauge('rate_limit_avg_wait', 'Average wait time')
            
            stats = limiter.get_stats()
            wait_rate.set(stats['wait_rate'])
            wait_time.set(stats['average_wait_time'])
        """
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
    """
    Global Registry for Rate Limiters (Singleton Pattern)
    
    This class maintains a central registry of all rate limiters in the application,
    implementing the Registry design pattern with singleton semantics.
    
    Benefits:
    ---------
    - Centralized management of all rate limiters
    - Prevents duplicate rate limiter instances
    - Easy monitoring and statistics collection
    - Simplified configuration management
    - Global reset capability for testing
    
    Design Pattern:
    ---------------
    This implements the Registry pattern, which provides:
    - Single point of access to all rate limiters
    - Lazy initialization of rate limiters
    - Automatic lifecycle management
    
    Thread Safety:
    --------------
    Class-level dictionary is thread-safe for read operations.
    Creation of new limiters should be done at application startup.
    
    Example:
    --------
        # Get or create rate limiter
        limiter = RateLimiterRegistry.get(
            "form_recognizer",
            rate_per_second=15,
            burst_capacity=30
        )
        
        # Later, reuse the same limiter
        limiter = RateLimiterRegistry.get("form_recognizer")
        
        # Get all stats for monitoring dashboard
        all_stats = RateLimiterRegistry.get_all_stats()
        for name, stats in all_stats.items():
            print(f"{name}: {stats['wait_rate']}% wait rate")
        
        # Reset all for testing
        RateLimiterRegistry.reset_all()
    
    Use Cases:
    ----------
    - Application-wide rate limiting coordination
    - Monitoring dashboard (get_all_stats())
    - Testing (reset_all())
    - Configuration management
    - Health checks
    
    Attributes:
        _limiters (Dict[str, RateLimiter]): Class-level registry of all limiters
    """
    
    # Class-level dictionary maintains all rate limiters
    _limiters: Dict[str, RateLimiter] = {}
    
    @classmethod
    def get(
        cls,
        name: str,
        rate_per_second: Optional[float] = None,
        burst_capacity: Optional[int] = None
    ) -> RateLimiter:
        """
        Get existing rate limiter or create new one.
        
        This method implements lazy initialization - rate limiters are
        created on first use. Once created, the same instance is reused.
        
        Args:
            name (str): Unique identifier for the rate limiter
            rate_per_second (float, optional): Token refill rate. Required if
                creating new limiter, ignored if limiter already exists.
            burst_capacity (int, optional): Maximum tokens. Defaults to rate_per_second.
        
        Returns:
            RateLimiter: Existing or newly created rate limiter instance
        
        Raises:
            ValueError: If limiter doesn't exist and no rate_per_second provided
        
        Example:
            # First call - creates new limiter
            limiter = RateLimiterRegistry.get("api", rate_per_second=10)
            
            # Subsequent calls - reuses same instance
            same_limiter = RateLimiterRegistry.get("api")
            assert limiter is same_limiter  # True
        """
        if name not in cls._limiters:
            if rate_per_second is None:
                raise ValueError(
                    f"Rate limiter '{name}' not found and no rate_per_second specified. "
                    f"Available limiters: {list(cls._limiters.keys())}"
                )
            cls._limiters[name] = RateLimiter(name, rate_per_second, burst_capacity)
        return cls._limiters[name]
    
    @classmethod
    def get_all(cls) -> Dict[str, RateLimiter]:
        """
        Get all registered rate limiters.
        
        Returns:
            Dict[str, RateLimiter]: Copy of the limiters dictionary
        
        Note:
            Returns a copy to prevent external modification of the registry.
        """
        return cls._limiters.copy()
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all rate limiters.
        
        Useful for:
        - Monitoring dashboards
        - Health check endpoints
        - Alerting systems
        - Capacity planning
        
        Returns:
            Dict[str, Dict[str, Any]]: Statistics for each rate limiter
        
        Example:
            # Expose via FastAPI endpoint
            @app.get("/metrics/rate-limiters")
            async def get_rate_limiter_metrics():
                return RateLimiterRegistry.get_all_stats()
            
            # Check for issues
            stats = RateLimiterRegistry.get_all_stats()
            for name, data in stats.items():
                if data['wait_rate'] > 50:
                    alert(f"High rate limit pressure on {name}")
        """
        return {
            name: limiter.get_stats()
            for name, limiter in cls._limiters.items()
        }
    
    @classmethod
    def reset_all(cls):
        """
        Reset all rate limiters to initial state.
        
        This is primarily useful for:
        - Unit tests (ensure clean state)
        - Integration tests (reset between test cases)
        - Development/debugging
        
        Warning:
            This should NOT be called in production as it will discard
            all accumulated statistics and reset token counts.
        
        Example:
            # In pytest fixture
            @pytest.fixture(autouse=True)
            def reset_rate_limiters():
                yield
                RateLimiterRegistry.reset_all()
        """
        for limiter in cls._limiters.values():
            limiter.reset()


def rate_limit(
    name: str,
    rate_per_second: Optional[float] = None,
    burst_capacity: Optional[int] = None,
    tokens: int = 1
):
    """
    Decorator for rate-limiting functions and methods.
    
    This decorator automatically applies rate limiting to any function,
    supporting both sync and async functions. It acquires tokens before
    function execution, ensuring the rate limit is never exceeded.
    
    Features:
    ---------
    - Works with both sync and async functions
    - Automatic token acquisition before function call
    - Logging of rate limit events
    - Integration with RateLimiterRegistry
    - Zero code changes to decorated function
    
    Parameters:
    -----------
    name : str
        Unique identifier for the rate limiter. All functions with the same
        name share the same rate limit pool.
    rate_per_second : float, optional
        Maximum calls per second. Required if rate limiter doesn't exist yet.
    burst_capacity : int, optional
        Maximum burst size. Defaults to rate_per_second if not specified.
    tokens : int, default=1
        Number of tokens consumed per call. Use >1 for expensive operations.
    
    Returns:
    --------
    Callable
        Decorated function that enforces rate limiting
    
    Usage Examples:
    ---------------
    
    Basic Usage:
        @rate_limit("api_calls", rate_per_second=10)
        async def call_external_api(url: str):
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()
    
    With Burst Capacity:
        @rate_limit("database", rate_per_second=50, burst_capacity=100)
        async def query_database(sql: str):
            return await db.execute(sql)
    
    Variable Cost (Multiple Tokens):
        @rate_limit("expensive_ops", rate_per_second=5, tokens=3)
        async def expensive_operation():
            # This operation costs 3 tokens (3x more expensive)
            return await heavy_computation()
    
    Shared Rate Limit:
        # Both functions share the same rate limit pool
        @rate_limit("api", rate_per_second=10)
        async def get_user(id: int):
            return await api.get(f"/users/{id}")
        
        @rate_limit("api")  # Reuses existing "api" limiter
        async def update_user(id: int, data: dict):
            return await api.put(f"/users/{id}", json=data)
    
    With Sync Functions:
        @rate_limit("legacy_api", rate_per_second=5)
        def sync_api_call(endpoint: str):
            response = requests.get(endpoint)
            return response.json()
    
    Class Methods:
        class APIClient:
            @rate_limit("api", rate_per_second=10)
            async def fetch_data(self, endpoint: str):
                return await self.client.get(endpoint)
    
    Error Handling:
        @rate_limit("critical_api", rate_per_second=5)
        async def critical_operation():
            try:
                return await api.call()
            except Exception as e:
                logger.error(f"Failed: {e}")
                raise
    
    Monitoring:
        @rate_limit("monitored_api", rate_per_second=10)
        async def monitored_call():
            result = await api.call()
            # Rate limit stats automatically tracked
            return result
        
        # Later, check stats
        stats = RateLimiterRegistry.get("monitored_api").get_stats()
        print(f"Wait rate: {stats['wait_rate']}%")
    
    Performance Notes:
    ------------------
    - Async functions: Zero overhead, non-blocking waits
    - Sync functions: Uses asyncio.run() (small overhead)
    - Token acquisition: O(1) time complexity
    - Memory: ~1KB per unique rate limiter name
    
    Best Practices:
    ---------------
    1. Use descriptive names: "azure_form_recognizer" not "api1"
    2. Set realistic rates based on service quotas
    3. Use burst_capacity for bursty traffic patterns
    4. Monitor wait_rate to tune limits
    5. Share limiters across related operations
    
    Common Patterns:
    ----------------
    
    Tiered Rate Limiting:
        @rate_limit("tier1", rate_per_second=100)  # Premium users
        @rate_limit("tier2", rate_per_second=10)   # Free users
    
    Per-Service Limiting:
        @rate_limit("azure_openai", rate_per_second=8)
        @rate_limit("azure_form_recognizer", rate_per_second=15)
        @rate_limit("database", rate_per_second=50)
    
    Cost-Based Limiting:
        @rate_limit("tokens", tokens=1)    # Light operation
        @rate_limit("tokens", tokens=5)    # Medium operation
        @rate_limit("tokens", tokens=10)   # Heavy operation
    
    See Also:
    ---------
    - RateLimiter.acquire(): For programmatic token acquisition
    - RateLimiter.try_acquire(): For non-blocking rate limiting
    - RateLimiterRegistry: For managing multiple rate limiters
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

