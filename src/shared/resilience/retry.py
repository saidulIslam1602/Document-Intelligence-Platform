"""
Retry Logic with Exponential Backoff
Provides automatic retry functionality for transient failures
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
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
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
    Decorator for automatic retry with exponential backoff
    
    Usage:
        @retry(max_retries=3, initial_delay=1.0)
        async def my_function():
            # Your code here
            pass
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

