"""
HTTP Client Connection Pool
Efficient connection reuse for all HTTP requests across microservices
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from ..config.enhanced_settings import get_settings
from ..resilience.retry import retry_with_backoff, retry_on_http_error

logger = logging.getLogger(__name__)


class HTTPClientPool:
    """Singleton HTTP client pool for efficient connection reuse"""
    
    _instance: Optional[httpx.AsyncClient] = None
    _sync_instance: Optional[httpx.Client] = None
    
    @classmethod
    def get_client(cls, timeout_config: Optional[Dict[str, float]] = None) -> httpx.AsyncClient:
        """
        Get or create async HTTP client with connection pooling
        
        Args:
            timeout_config: Optional timeout configuration override
            
        Returns:
            httpx.AsyncClient: Configured async HTTP client with connection pool
        """
        if cls._instance is None:
            settings = get_settings()
            perf = settings.performance
            
            # Configure timeouts
            if timeout_config:
                timeout = httpx.Timeout(**timeout_config)
            else:
                timeout = httpx.Timeout(
                    connect=perf.http_timeout_connect,
                    read=perf.http_timeout_read,
                    write=perf.http_timeout_write,
                    pool=perf.http_timeout_pool
                )
            
            # Configure connection limits
            limits = httpx.Limits(
                max_keepalive_connections=perf.http_max_keepalive,
                max_connections=perf.http_max_connections,
                keepalive_expiry=30.0  # Keep connections alive for 30 seconds
            )
            
            # Create client with connection pooling
            cls._instance = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                http2=perf.http2_enabled,  # Enable HTTP/2 for multiplexing
                follow_redirects=True,
                verify=True  # Verify SSL certificates
            )
            
            logger.info(
                f"HTTP client pool initialized: "
                f"max_connections={perf.http_max_connections}, "
                f"max_keepalive={perf.http_max_keepalive}, "
                f"http2={perf.http2_enabled}"
            )
        
        return cls._instance
    
    @classmethod
    def get_sync_client(cls, timeout_config: Optional[Dict[str, float]] = None) -> httpx.Client:
        """
        Get or create sync HTTP client with connection pooling
        
        Args:
            timeout_config: Optional timeout configuration override
            
        Returns:
            httpx.Client: Configured sync HTTP client with connection pool
        """
        if cls._sync_instance is None:
            settings = get_settings()
            perf = settings.performance
            
            # Configure timeouts
            if timeout_config:
                timeout = httpx.Timeout(**timeout_config)
            else:
                timeout = httpx.Timeout(
                    connect=perf.http_timeout_connect,
                    read=perf.http_timeout_read,
                    write=perf.http_timeout_write,
                    pool=perf.http_timeout_pool
                )
            
            # Configure connection limits
            limits = httpx.Limits(
                max_keepalive_connections=perf.http_max_keepalive,
                max_connections=perf.http_max_connections,
                keepalive_expiry=30.0
            )
            
            # Create sync client with connection pooling
            cls._sync_instance = httpx.Client(
                timeout=timeout,
                limits=limits,
                http2=perf.http2_enabled,
                follow_redirects=True,
                verify=True
            )
            
            logger.info("Sync HTTP client pool initialized")
        
        return cls._sync_instance
    
    @classmethod
    async def close(cls):
        """Close the async HTTP client pool"""
        if cls._instance:
            await cls._instance.aclose()
            cls._instance = None
            logger.info("HTTP client pool closed")
    
    @classmethod
    def close_sync(cls):
        """Close the sync HTTP client pool"""
        if cls._sync_instance:
            cls._sync_instance.close()
            cls._sync_instance = None
            logger.info("Sync HTTP client pool closed")
    
    @classmethod
    async def close_all(cls):
        """Close all HTTP client pools"""
        await cls.close()
        cls.close_sync()


# Convenience functions
def get_http_client() -> httpx.AsyncClient:
    """Get async HTTP client from pool"""
    return HTTPClientPool.get_client()


def get_sync_http_client() -> httpx.Client:
    """Get sync HTTP client from pool"""
    return HTTPClientPool.get_sync_client()


async def close_http_clients():
    """Close all HTTP clients"""
    await HTTPClientPool.close_all()


# Context manager for request-scoped client
class HTTPClient:
    """Context manager for HTTP client with automatic cleanup"""
    
    def __init__(self, timeout_config: Optional[Dict[str, float]] = None):
        self.timeout_config = timeout_config
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> httpx.AsyncClient:
        """Get client from pool"""
        self.client = HTTPClientPool.get_client(self.timeout_config)
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Client is managed by pool, no cleanup needed"""
        pass


# HTTP request helpers with automatic retry
async def make_request_with_retry(
    method: str,
    url: str,
    max_retries: Optional[int] = None,
    **kwargs
) -> httpx.Response:
    """
    Make HTTP request with automatic retry using exponential backoff
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        max_retries: Maximum number of retries (default from config)
        **kwargs: Additional arguments for httpx request
        
    Returns:
        httpx.Response: HTTP response
        
    Raises:
        httpx.HTTPError: If request fails after all retries
        
    Example:
        response = await make_request_with_retry("GET", "https://api.example.com/data")
        data = response.json()
    """
    client = get_http_client()
    
    async def _make_request():
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    # Use retry with exponential backoff
    return await retry_with_backoff(
        _make_request,
        max_retries=max_retries,
        retryable_exceptions=(
            httpx.HTTPError,
            httpx.ConnectError,
            httpx.TimeoutException
        )
    )


# Convenience methods for common HTTP methods with retry
async def get_with_retry(url: str, **kwargs) -> httpx.Response:
    """GET request with automatic retry"""
    return await make_request_with_retry("GET", url, **kwargs)


async def post_with_retry(url: str, **kwargs) -> httpx.Response:
    """POST request with automatic retry"""
    return await make_request_with_retry("POST", url, **kwargs)


async def put_with_retry(url: str, **kwargs) -> httpx.Response:
    """PUT request with automatic retry"""
    return await make_request_with_retry("PUT", url, **kwargs)


async def delete_with_retry(url: str, **kwargs) -> httpx.Response:
    """DELETE request with automatic retry"""
    return await make_request_with_retry("DELETE", url, **kwargs)


async def patch_with_retry(url: str, **kwargs) -> httpx.Response:
    """PATCH request with automatic retry"""
    return await make_request_with_retry("PATCH", url, **kwargs)


# Health check for HTTP client pool
async def check_http_pool_health() -> Dict[str, Any]:
    """Check HTTP client pool health"""
    try:
        client = get_http_client()
        return {
            "status": "healthy",
            "http2_enabled": client._transport._pool._http2 if hasattr(client, '_transport') else False,
            "active_connections": len(client._transport._pool._connections) if hasattr(client, '_transport') else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

