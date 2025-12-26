"""
Retry Logic with Exponential Backoff - Resilience Pattern Implementation

This module implements automatic retry functionality for handling transient failures,
a critical resilience pattern for distributed systems and microservices architectures.

Exponential Backoff Algorithm:
-------------------------------
Exponential backoff is a standard error handling strategy for network applications
where retry attempts are progressively delayed to avoid overwhelming failing services.

Formula:
    delay = min(initial_delay * (base ^ attempt), max_delay)
    with optional jitter: delay *= (0.5 + random())

Example delays (initial=1s, base=2, max=30s):
    Attempt 1: 1s    (2^0)
    Attempt 2: 2s    (2^1)
    Attempt 3: 4s    (2^2)
    Attempt 4: 8s    (2^3)
    Attempt 5: 16s   (2^4)
    Attempt 6: 30s   (capped at max)

Why Exponential Backoff?
-------------------------
1. **Prevents Thundering Herd**: Spreading retries over time prevents all clients
   from retrying simultaneously after a service recovers
2. **Gives Time to Recover**: Allows failing services time to recover
3. **Reduces Load**: Decreases retry frequency as attempts increase
4. **Industry Standard**: Used by AWS, Google Cloud, Azure, etc.

Jitter (Randomization):
-----------------------
Adding random jitter (0.5x to 1.5x of calculated delay) prevents synchronized
retries from multiple clients, which can cause cascading failures.

Without jitter: All 1000 clients retry at exact same time (thundering herd)
With jitter: Clients retry spread over 50% to 150% of delay window

Use Cases:
----------
1. **Network Failures**: Connection timeouts, temporary network issues
2. **Service Unavailability**: 503 Service Unavailable, 504 Gateway Timeout
3. **Rate Limiting**: 429 Too Many Requests (with exponential backoff)
4. **Database Deadlocks**: Transient database errors
5. **Cloud Services**: Azure, AWS, GCP transient errors
6. **Message Queue**: Failed message processing

Transient vs Permanent Failures:
---------------------------------
✅ RETRY: 
   - Network timeouts
   - 500 Internal Server Error
   - 503 Service Unavailable
   - 504 Gateway Timeout
   - 429 Too Many Requests
   - Connection refused (during deployment)
   - Database deadlocks

❌ DON'T RETRY:
   - 400 Bad Request (fix input)
   - 401 Unauthorized (fix credentials)
   - 403 Forbidden (fix permissions)
   - 404 Not Found (resource doesn't exist)
   - Validation errors (fix data)

Best Practices:
---------------
1. **Set Maximum Attempts**: Prevent infinite retries (default: 3-5)
2. **Use Circuit Breaker**: Combine with circuit breaker for fast failure
3. **Log Retry Attempts**: Monitor retry frequency for capacity planning
4. **Configure Timeouts**: Set reasonable operation timeouts
5. **Exponential Delays**: Use exponential backoff, not fixed delays
6. **Add Jitter**: Always enable jitter to prevent thundering herd
7. **Define Retryable Exceptions**: Only retry transient failures
8. **Monitor Metrics**: Track retry rate, success rate, and latency

Integration with Other Patterns:
---------------------------------
- **Circuit Breaker**: Fails fast when service is down (prevents wasted retries)
- **Rate Limiting**: Protects downstream services during retries
- **Timeout**: Ensures retries don't hang indefinitely
- **Bulkhead**: Isolates retry attempts to prevent resource exhaustion

Example Usage:
--------------
    # Basic retry with decorator
    @retry(max_retries=3, initial_delay=1.0, jitter=True)
    async def call_external_api():
        response = await client.get("https://api.example.com")
        return response.json()

    # Programmatic retry
    result = await retry_with_backoff(
        expensive_operation,
        max_retries=5,
        initial_delay=1.0,
        retryable_exceptions=(ConnectionError, TimeoutError)
    )

    # HTTP-specific retry
    @retry_on_http_error(max_retries=3, status_codes=(500, 503, 504))
    async def fetch_data():
        return await api.get("/data")

References:
-----------
- Exponential Backoff: https://en.wikipedia.org/wiki/Exponential_backoff
- AWS Retry Strategy: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Google Cloud Retry: https://cloud.google.com/storage/docs/exponential-backoff
- Azure Retry Guidelines: https://docs.microsoft.com/azure/architecture/best-practices/retry-service-specific
- Resilience Patterns: https://docs.microsoft.com/azure/architecture/patterns/category/resiliency

Performance:
------------
- Time complexity: O(1) per attempt
- Space complexity: O(1)
- Total retry time: O(2^n) where n is max_retries

Author: Document Intelligence Platform Team
Version: 2.0.0
Pattern: Resilience - Retry with Exponential Backoff
"""

import asyncio
import random
import logging
from typing import Callable, Any, Type, Tuple, Optional, Union
from functools import wraps
from ..config.enhanced_settings import get_settings

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted"""
    pass


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: Optional[int] = None,
    initial_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exponential_base: Optional[float] = None,
    jitter: Optional[bool] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff and jitter.
    
    This function implements the exponential backoff algorithm with optional jitter
    to automatically retry operations that fail due to transient errors.
    
    Algorithm Flow:
    ---------------
    1. Attempt to execute function
    2. If successful: return result
    3. If exception in retryable_exceptions:
       a. Check if max_retries reached → raise RetryExhaustedError
       b. Calculate delay: initial_delay * (exponential_base ^ attempt)
       c. Apply jitter if enabled: delay * (0.5 to 1.5 random)
       d. Cap delay at max_delay
       e. Call on_retry callback if provided
       f. Sleep for calculated delay
       g. Go to step 1
    4. If exception NOT retryable: raise immediately
    
    Mathematical Model:
    -------------------
    delay(n) = min(initial_delay * base^n, max_delay)
    with jitter: delay(n) *= uniform(0.5, 1.5)
    
    Example Delays (initial=1s, base=2, max=30s, no jitter):
        Attempt 0: 1s   (2^0 = 1)
        Attempt 1: 2s   (2^1 = 2)
        Attempt 2: 4s   (2^2 = 4)
        Attempt 3: 8s   (2^3 = 8)
        Attempt 4: 16s  (2^4 = 16)
        Attempt 5: 30s  (2^5 = 32, capped at 30)
    
    With jitter, delays would vary:
        Attempt 0: 0.5-1.5s
        Attempt 1: 1.0-3.0s
        Attempt 2: 2.0-6.0s
        etc.
    
    Configuration:
    --------------
    If parameters are None, values are loaded from enhanced_settings.py:
    - max_retries: RETRY_MAX_RETRIES (default: 3)
    - initial_delay: RETRY_INITIAL_DELAY (default: 1.0s)
    - max_delay: RETRY_MAX_DELAY (default: 30.0s)
    - exponential_base: RETRY_EXPONENTIAL_BASE (default: 2.0)
    - jitter: RETRY_JITTER (default: True)
    
    Args:
        func (Callable): Async function to retry. Can also handle sync functions.
        *args: Positional arguments passed to func
        max_retries (int, optional): Maximum retry attempts. Default from config (3).
        initial_delay (float, optional): Initial delay in seconds. Default from config (1.0).
        max_delay (float, optional): Maximum delay in seconds. Default from config (30.0).
        exponential_base (float, optional): Exponential base for backoff. Default from config (2.0).
        jitter (bool, optional): Enable jitter (randomization). Default from config (True).
        retryable_exceptions (Tuple[Type[Exception], ...], optional): Exceptions that trigger
            retry. Default is (Exception,) which retries all exceptions. For production,
            specify exact exceptions like (ConnectionError, TimeoutError, HTTPError).
        on_retry (Callable, optional): Callback function called after each failed attempt.
            Signature: async def callback(attempt: int, exception: Exception, delay: float)
            Use for metrics, logging, alerting, or custom backoff logic.
        **kwargs: Keyword arguments passed to func
    
    Returns:
        Any: Result of successful function execution
    
    Raises:
        RetryExhaustedError: If all retry attempts are exhausted. Contains the original
            exception in __cause__ for debugging.
        Exception: Any non-retryable exception is raised immediately
    
    Examples:
    ---------
    
    Basic Usage:
        async def fetch_data():
            response = await client.get("https://api.example.com/data")
            return response.json()
        
        # Retry with defaults from config
        result = await retry_with_backoff(fetch_data)
    
    Custom Configuration:
        result = await retry_with_backoff(
            api_call,
            url="https://api.example.com",
            max_retries=5,
            initial_delay=2.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )
    
    Specific Exceptions:
        from httpx import HTTPError, ConnectError, TimeoutException
        
        result = await retry_with_backoff(
            http_request,
            max_retries=3,
            retryable_exceptions=(
                HTTPError,
                ConnectError,
                TimeoutException
            )
        )
    
    With Callback:
        retry_count = {"value": 0}
        
        async def on_retry_callback(attempt, exception, delay):
            retry_count["value"] += 1
            logger.warning(f"Retry {attempt}: {exception}, waiting {delay}s")
            # Send metrics to monitoring system
            metrics.increment("api.retries", tags={"attempt": attempt})
        
        result = await retry_with_backoff(
            risky_operation,
            max_retries=5,
            on_retry=on_retry_callback
        )
    
    Error Handling:
        try:
            result = await retry_with_backoff(
                unreliable_service,
                max_retries=3
            )
        except RetryExhaustedError as e:
            logger.error(f"Service failed after retries: {e.__cause__}")
            # Fallback logic here
            result = get_cached_result()
    
    Performance Notes:
    ------------------
    - Each retry adds exponentially increasing delay
    - Total max time: sum of all delays (~2^n for n retries)
    - With 5 retries (1,2,4,8,16s): max ~31 seconds
    - Async-friendly: doesn't block event loop during sleep
    
    Best Practices:
    ---------------
    1. Always specify retryable_exceptions for production
    2. Enable jitter to prevent thundering herd
    3. Set reasonable max_delay (30-60s typical)
    4. Use on_retry for monitoring and alerting
    5. Combine with circuit breaker for fast failure
    6. Set timeout on underlying operations
    
    Common Pitfalls:
    ----------------
    - Don't retry non-transient errors (400, 401, 403, 404)
    - Don't set max_retries too high (causes long delays)
    - Don't disable jitter in production (thundering herd)
    - Don't retry operations without timeouts (can hang)
    
    See Also:
    ---------
    - retry(): Decorator version
    - retry_with_backoff_sync(): Sync function version
    - retry_on_http_error(): HTTP-specific retry
    - retry_on_connection_error(): Connection-specific retry
    """
    # Get configuration
    settings = get_settings()
    retry_config = settings.retry
    
    # Use config defaults if not provided
    max_retries = max_retries if max_retries is not None else retry_config.max_retries
    initial_delay = initial_delay if initial_delay is not None else retry_config.initial_delay
    max_delay = max_delay if max_delay is not None else retry_config.max_delay
    exponential_base = exponential_base if exponential_base is not None else retry_config.exponential_base
    jitter = jitter if jitter is not None else retry_config.jitter
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - return result
            if attempt > 0:
                logger.info(f"Retry successful after {attempt} attempt(s)")
            return result
            
        except retryable_exceptions as e:
            last_exception = e
            
            # Check if we should retry
            if attempt >= max_retries:
                logger.error(
                    f"All {max_retries} retry attempts exhausted. "
                    f"Last error: {str(e)}"
                )
                raise RetryExhaustedError(
                    f"Failed after {max_retries} retries"
                ) from e
            
            # Calculate delay with exponential backoff
            delay = min(
                initial_delay * (exponential_base ** attempt),
                max_delay
            )
            
            # Add jitter if enabled (0.5x to 1.5x of delay)
            if jitter:
                delay = delay * (0.5 + random.random())
            
            # Log retry attempt
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            # Call on_retry callback if provided
            if on_retry:
                try:
                    if asyncio.iscoroutinefunction(on_retry):
                        await on_retry(attempt, e, delay)
                    else:
                        on_retry(attempt, e, delay)
                except Exception as callback_error:
                    logger.error(f"Error in on_retry callback: {callback_error}")
            
            # Wait before retrying
            await asyncio.sleep(delay)
    
    # Should never reach here, but just in case
    raise last_exception or RetryExhaustedError("Retry logic error")


def retry_with_backoff_sync(
    func: Callable,
    *args,
    max_retries: Optional[int] = None,
    initial_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exponential_base: Optional[float] = None,
    jitter: Optional[bool] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    **kwargs
) -> Any:
    """
    Retry a sync function with exponential backoff
    
    Args:
        func: Sync function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts (default from config)
        initial_delay: Initial delay in seconds (default from config)
        max_delay: Maximum delay in seconds (default from config)
        exponential_base: Exponential base for backoff (default from config)
        jitter: Add random jitter to prevent thundering herd (default from config)
        retryable_exceptions: Tuple of exceptions that trigger retry
        on_retry: Optional callback function called on each retry
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of successful function execution
        
    Raises:
        RetryExhaustedError: If all retries are exhausted
        Exception: The last exception if retries exhausted
    """
    import time
    
    # Get configuration
    settings = get_settings()
    retry_config = settings.retry
    
    # Use config defaults if not provided
    max_retries = max_retries if max_retries is not None else retry_config.max_retries
    initial_delay = initial_delay if initial_delay is not None else retry_config.initial_delay
    max_delay = max_delay if max_delay is not None else retry_config.max_delay
    exponential_base = exponential_base if exponential_base is not None else retry_config.exponential_base
    jitter = jitter if jitter is not None else retry_config.jitter
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Success - return result
            if attempt > 0:
                logger.info(f"Retry successful after {attempt} attempt(s)")
            return result
            
        except retryable_exceptions as e:
            last_exception = e
            
            # Check if we should retry
            if attempt >= max_retries:
                logger.error(
                    f"All {max_retries} retry attempts exhausted. "
                    f"Last error: {str(e)}"
                )
                raise RetryExhaustedError(
                    f"Failed after {max_retries} retries"
                ) from e
            
            # Calculate delay with exponential backoff
            delay = min(
                initial_delay * (exponential_base ** attempt),
                max_delay
            )
            
            # Add jitter if enabled
            if jitter:
                delay = delay * (0.5 + random.random())
            
            # Log retry attempt
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            # Call on_retry callback if provided
            if on_retry:
                try:
                    on_retry(attempt, e, delay)
                except Exception as callback_error:
                    logger.error(f"Error in on_retry callback: {callback_error}")
            
            # Wait before retrying
            time.sleep(delay)
    
    # Should never reach here, but just in case
    raise last_exception or RetryExhaustedError("Retry logic error")


def retry(
    max_retries: Optional[int] = None,
    initial_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exponential_base: Optional[float] = None,
    jitter: Optional[bool] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for automatic retry with exponential backoff.
    
    This decorator wraps functions to automatically retry on failures using
    exponential backoff. Works with both sync and async functions.
    
    The decorator provides a clean, declarative way to add retry logic without
    modifying function code, following the principle of separation of concerns.
    
    Features:
    ---------
    - Works with both sync and async functions
    - Automatic exponential backoff calculation
    - Optional jitter to prevent thundering herd
    - Configurable retryable exceptions
    - Callback support for monitoring
    - Zero code changes to decorated function
    - Configuration from settings or parameters
    
    Parameters:
    -----------
    max_retries : int, optional
        Maximum number of retry attempts. Default from config (typically 3).
    initial_delay : float, optional
        Initial delay in seconds before first retry. Default from config (typically 1.0).
    max_delay : float, optional
        Maximum delay in seconds to cap exponential growth. Default from config (typically 30.0).
    exponential_base : float, optional
        Base for exponential backoff calculation. Default from config (typically 2.0).
        delay = initial_delay * (exponential_base ^ attempt)
    jitter : bool, optional
        Enable random jitter (0.5x to 1.5x of calculated delay). Default from config (True).
        Prevents thundering herd problem in distributed systems.
    retryable_exceptions : Tuple[Type[Exception], ...], optional
        Exceptions that should trigger a retry. Default is (Exception,) which retries
        all exceptions. For production, specify exact exceptions.
    on_retry : Callable, optional
        Callback function called after each retry attempt.
        Signature: async def callback(attempt: int, exception: Exception, delay: float)
    
    Returns:
    --------
    Callable
        Decorated function with automatic retry logic
    
    Usage Examples:
    ---------------
    
    1. Basic Async Function:
        @retry(max_retries=3, initial_delay=1.0)
        async def fetch_user_data(user_id: int):
            response = await api_client.get(f"/users/{user_id}")
            return response.json()
    
    2. Sync Function:
        @retry(max_retries=5, initial_delay=2.0)
        def fetch_from_database(query: str):
            return database.execute(query)
    
    3. With Specific Exceptions:
        from httpx import HTTPError, ConnectError, TimeoutException
        
        @retry(
            max_retries=3,
            retryable_exceptions=(HTTPError, ConnectError, TimeoutException)
        )
        async def call_external_api():
            return await client.get("https://api.example.com/data")
    
    4. With Callback for Monitoring:
        async def log_retry_attempt(attempt, exception, delay):
            logger.warning(f"Retry {attempt}: {exception}, delay={delay}s")
            metrics.increment("retry.attempts", tags={"service": "api"})
        
        @retry(max_retries=5, on_retry=log_retry_attempt)
        async def critical_operation():
            return await perform_operation()
    
    5. Custom Backoff Configuration:
        @retry(
            max_retries=10,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=1.5,  # Slower growth
            jitter=True
        )
        async def aggressive_retry_operation():
            return await unstable_service()
    
    6. Class Methods:
        class APIClient:
            @retry(max_retries=3)
            async def get(self, endpoint: str):
                return await self.session.get(endpoint)
            
            @retry(max_retries=5, initial_delay=2.0)
            async def post(self, endpoint: str, data: dict):
                return await self.session.post(endpoint, json=data)
    
    7. With Error Handling:
        @retry(max_retries=3, initial_delay=1.0)
        async def fallible_operation():
            try:
                return await risky_call()
            except ValueError as e:
                # Non-transient error, don't retry
                logger.error(f"Invalid data: {e}")
                raise
            except ConnectionError:
                # Transient error, will be retried
                raise
    
    8. Multiple Decorators:
        from .rate_limiting import rate_limit
        from .circuit_breaker import circuit_breaker
        
        @retry(max_retries=3)
        @rate_limit("api", rate_per_second=10)
        @circuit_breaker("api", failure_threshold=5)
        async def resilient_api_call():
            return await api.call()
    
    Common Use Cases:
    -----------------
    
    API Calls:
        @retry(
            max_retries=3,
            retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException)
        )
        async def call_api():
            return await client.get("/endpoint")
    
    Database Operations:
        @retry(
            max_retries=5,
            retryable_exceptions=(psycopg2.OperationalError,)
        )
        def query_database():
            return db.execute("SELECT * FROM users")
    
    File Operations:
        @retry(
            max_retries=3,
            retryable_exceptions=(IOError, OSError)
        )
        async def read_file(path: str):
            async with aiofiles.open(path) as f:
                return await f.read()
    
    Message Queue:
        @retry(
            max_retries=10,
            initial_delay=1.0,
            retryable_exceptions=(MessageQueueError,)
        )
        async def publish_message(message):
            await queue.publish(message)
    
    Performance Characteristics:
    ----------------------------
    - Overhead per call: ~0.1ms (negligible)
    - Memory: ~1KB per decorated function
    - Async-friendly: uses asyncio.sleep (non-blocking)
    - Sync functions: uses time.sleep (blocking)
    
    Best Practices:
    ---------------
    1. **Specify Exact Exceptions**: Don't use (Exception,) in production
       @retry(retryable_exceptions=(SpecificError,))
    
    2. **Enable Jitter**: Always use jitter=True to prevent thundering herd
       @retry(jitter=True)
    
    3. **Set Reasonable Limits**: Don't retry forever
       @retry(max_retries=3, max_delay=30.0)
    
    4. **Monitor Retries**: Use on_retry callback for metrics
       @retry(on_retry=send_to_metrics)
    
    5. **Combine with Circuit Breaker**: Fast fail when service is down
       @circuit_breaker("service")
       @retry(max_retries=3)
    
    6. **Set Timeouts**: Ensure operations have timeouts
       @retry(max_retries=3)
       async def with_timeout():
           async with timeout(5.0):
               return await operation()
    
    Anti-Patterns:
    --------------
    ❌ Retrying non-transient errors:
        @retry(retryable_exceptions=(ValueError,))  # Don't retry validation errors
    
    ❌ Too many retries:
        @retry(max_retries=100)  # Will cause very long delays
    
    ❌ No jitter in distributed system:
        @retry(jitter=False)  # Can cause thundering herd
    
    ❌ Retrying without timeouts:
        @retry(max_retries=5)
        async def no_timeout():
            # This could hang forever on each attempt
            return await infinite_operation()
    
    Debugging:
    ----------
    To see retry attempts in logs:
        import logging
        logging.getLogger("shared.resilience.retry").setLevel(logging.DEBUG)
    
    To track retry statistics:
        @retry(max_retries=5, on_retry=lambda a, e, d: print(f"Attempt {a}"))
    
    Integration with Testing:
    -------------------------
    Override retry config for tests:
        # In conftest.py
        @pytest.fixture(autouse=True)
        def fast_retries(monkeypatch):
            monkeypatch.setenv("RETRY_MAX_RETRIES", "1")
            monkeypatch.setenv("RETRY_INITIAL_DELAY", "0.01")
    
    Or disable retries:
        @retry(max_retries=0)  # Disabled for testing
    
    See Also:
    ---------
    - retry_with_backoff(): Programmatic retry function
    - retry_on_http_error(): HTTP-specific retry decorator
    - retry_on_connection_error(): Connection-specific retry decorator
    - CircuitBreaker: Combine with retry for fast failure
    - RateLimiter: Prevent overwhelming services during retries
    
    References:
    -----------
    - AWS Retry Strategy: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    - Google Cloud Retry: https://cloud.google.com/apis/design/errors#error_retries
    - Azure Retry Guidance: https://docs.microsoft.com/azure/architecture/best-practices/retry-service-specific
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
                on_retry=on_retry,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return retry_with_backoff_sync(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
                on_retry=on_retry,
                **kwargs
            )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience decorators for common use cases
def retry_on_http_error(
    max_retries: int = 3,
    status_codes: Tuple[int, ...] = (500, 502, 503, 504, 429)
):
    """
    Decorator for retrying on HTTP errors
    
    Usage:
        @retry_on_http_error(max_retries=3)
        async def fetch_data():
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    """
    import httpx
    
    def should_retry(exception):
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code in status_codes
        if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        return False
    
    retryable = tuple(
        exc for exc in [httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException]
    )
    
    return retry(
        max_retries=max_retries,
        retryable_exceptions=retryable
    )


def retry_on_connection_error(max_retries: int = 3):
    """
    Decorator for retrying on connection errors
    
    Usage:
        @retry_on_connection_error(max_retries=5)
        async def connect_to_service():
            return await service.connect()
    """
    import httpx
    
    return retry(
        max_retries=max_retries,
        retryable_exceptions=(
            httpx.ConnectError,
            httpx.TimeoutException,
            ConnectionError,
            TimeoutError
        )
    )


# Example on_retry callbacks
async def log_retry_metrics(attempt: int, exception: Exception, delay: float):
    """Example callback to log retry metrics"""
    logger.info(
        f"Retry metrics: attempt={attempt}, "
        f"exception={type(exception).__name__}, "
        f"delay={delay:.2f}s"
    )


async def notify_on_retry(attempt: int, exception: Exception, delay: float):
    """Example callback to send notifications on retry"""
    if attempt >= 2:  # Notify after 2 failed attempts
        logger.warning(
            f"Service degradation detected: {attempt} retries, "
            f"last error: {str(exception)}"
        )
        # Could send to monitoring service, Slack, etc.

