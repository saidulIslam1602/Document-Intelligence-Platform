"""
Resilience Module
Provides retry logic, circuit breakers, and other resilience patterns
"""

from .retry import (
    retry,
    retry_with_backoff,
    retry_with_backoff_sync,
    retry_on_http_error,
    retry_on_connection_error,
    RetryExhaustedError,
    log_retry_metrics,
    notify_on_retry
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitBreakerError,
    circuit_breaker,
    form_recognizer_circuit_breaker,
    openai_circuit_breaker,
    database_circuit_breaker,
    redis_circuit_breaker
)

__all__ = [
    # Retry
    "retry",
    "retry_with_backoff",
    "retry_with_backoff_sync",
    "retry_on_http_error",
    "retry_on_connection_error",
    "RetryExhaustedError",
    "log_retry_metrics",
    "notify_on_retry",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitState",
    "CircuitBreakerError",
    "circuit_breaker",
    "form_recognizer_circuit_breaker",
    "openai_circuit_breaker",
    "database_circuit_breaker",
    "redis_circuit_breaker"
]

