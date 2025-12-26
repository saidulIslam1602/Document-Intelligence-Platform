"""
HTTP utilities and connection pooling
"""

from .client_pool import (
    HTTPClientPool,
    get_http_client,
    get_sync_http_client,
    close_http_clients,
    HTTPClient,
    make_request_with_retry,
    get_with_retry,
    post_with_retry,
    put_with_retry,
    delete_with_retry,
    patch_with_retry,
    check_http_pool_health
)

__all__ = [
    'HTTPClientPool',
    'get_http_client',
    'get_sync_http_client',
    'close_http_clients',
    'HTTPClient',
    'make_request_with_retry',
    'get_with_retry',
    'post_with_retry',
    'put_with_retry',
    'delete_with_retry',
    'patch_with_retry',
    'check_http_pool_health'
]

