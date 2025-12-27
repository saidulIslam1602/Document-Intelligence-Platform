"""Caching module for performance optimization"""

from .redis_cache import (
    RedisCache,
    cache,
    init_cache,
    close_cache,
    cache_get_or_set,
    invalidate_user_cache,
    invalidate_document_cache,
)

__all__ = [
    'RedisCache',
    'cache',
    'init_cache',
    'close_cache',
    'cache_get_or_set',
    'invalidate_user_cache',
    'invalidate_document_cache',
]

