"""
Circuit Breaker Pattern Implementation
Prevents cascading failures by stopping requests to failing services
"""

import asyncio
import logging
import time
from typing import Callable, Any, Optional, Dict
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
from ..config.enhanced_settings import get_settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"          # Normal operation, requests pass through
    OPEN = "open"              # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"    # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, all requests fail fast
    - HALF_OPEN: Testing if service recovered
    
    Transitions:
    - CLOSED → OPEN: After failure_threshold consecutive failures
    - OPEN → HALF_OPEN: After timeout period
    - HALF_OPEN → CLOSED: After successful request
    - HALF_OPEN → OPEN: After any failure
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: Optional[int] = None,
        timeout: Optional[float] = None,
        half_open_timeout: Optional[float] = None,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        Initialize circuit breaker
        
        Args:
            name: Circuit breaker name (for logging/monitoring)
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before transitioning to half-open
            half_open_timeout: Seconds to wait in half-open before trying again
            expected_exceptions: Exceptions that trigger circuit breaker
        """
        self.name = name
        
        # Get configuration
        settings = get_settings()
        circuit_config = settings.circuit_breaker
        
        self.failure_threshold = failure_threshold if failure_threshold is not None else circuit_config.failure_threshold
        self.timeout = timeout if timeout is not None else circuit_config.timeout
        self.half_open_timeout = half_open_timeout if half_open_timeout is not None else circuit_config.half_open_timeout
        self.expected_exceptions = expected_exceptions
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.opened_at: Optional[float] = None
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_rejections = 0
        
        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"failure_threshold={self.failure_threshold}, "
            f"timeout={self.timeout}s, "
            f"half_open_timeout={self.half_open_timeout}s"
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function fails
        """
        self.total_requests += 1
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                self.total_rejections += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Will retry in {self._time_until_retry():.1f}s"
                )
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - handle state transition
            self._on_success()
            return result
            
        except self.expected_exceptions as e:
            # Failure - handle state transition
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open state"""
        if self.opened_at is None:
            return False
        
        time_since_open = time.time() - self.opened_at
        return time_since_open >= self.timeout
    
    def _time_until_retry(self) -> float:
        """Calculate time until next retry attempt"""
        if self.opened_at is None:
            return 0.0
        
        time_since_open = time.time() - self.opened_at
        return max(0.0, self.timeout - time_since_open)
    
    def _transition_to_half_open(self):
        """Transition from OPEN to HALF_OPEN"""
        logger.info(f"CircuitBreaker '{self.name}': OPEN → HALF_OPEN (testing service)")
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
    
    def _on_success(self):
        """Handle successful request"""
        self.total_successes += 1
        self.last_success_time = time.time()
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            # Success in half-open state closes circuit
            logger.info(f"CircuitBreaker '{self.name}': HALF_OPEN → CLOSED (service recovered)")
            self.state = CircuitState.CLOSED
            self.opened_at = None
    
    def _on_failure(self):
        """Handle failed request"""
        self.total_failures += 1
        self.last_failure_time = time.time()
        self.failure_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open opens circuit again
            logger.warning(
                f"CircuitBreaker '{self.name}': HALF_OPEN → OPEN (service still failing)"
            )
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            self.failure_count = 0
            
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Too many failures, open circuit
                logger.error(
                    f"CircuitBreaker '{self.name}': CLOSED → OPEN "
                    f"(threshold reached: {self.failure_count}/{self.failure_threshold})"
                )
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
                self.failure_count = 0
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state and statistics"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "total_rejections": self.total_rejections,
            "success_rate": (self.total_successes / self.total_requests * 100) 
                if self.total_requests > 0 else 0.0,
            "rejection_rate": (self.total_rejections / self.total_requests * 100)
                if self.total_requests > 0 else 0.0,
            "last_success_time": datetime.fromtimestamp(self.last_success_time).isoformat()
                if self.last_success_time else None,
            "last_failure_time": datetime.fromtimestamp(self.last_failure_time).isoformat()
                if self.last_failure_time else None,
            "time_until_retry": self._time_until_retry() if self.state == CircuitState.OPEN else 0.0
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        logger.info(f"CircuitBreaker '{self.name}': Manual reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None


class CircuitBreakerRegistry:
    """Global registry for circuit breakers"""
    
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get(cls, name: str, **kwargs) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, **kwargs)
        return cls._breakers[name]
    
    @classmethod
    def get_all(cls) -> Dict[str, CircuitBreaker]:
        """Get all registered circuit breakers"""
        return cls._breakers.copy()
    
    @classmethod
    def get_all_states(cls) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers"""
        return {
            name: breaker.get_state()
            for name, breaker in cls._breakers.items()
        }
    
    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers"""
        for breaker in cls._breakers.values():
            breaker.reset()


def circuit_breaker(
    name: str,
    failure_threshold: Optional[int] = None,
    timeout: Optional[float] = None,
    expected_exceptions: tuple = (Exception,)
):
    """
    Decorator for circuit breaker protection
    
    Usage:
        @circuit_breaker("external_api", failure_threshold=5, timeout=60.0)
        async def call_external_api():
            response = await client.get(url)
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        breaker = CircuitBreakerRegistry.get(
            name,
            failure_threshold=failure_threshold,
            timeout=timeout,
            expected_exceptions=expected_exceptions
        )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use asyncio.run for circuit breaker logic
            async def _async_call():
                return await breaker.call(lambda: func(*args, **kwargs))
            return asyncio.run(_async_call())
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience decorators for common services
def form_recognizer_circuit_breaker(func: Callable) -> Callable:
    """Circuit breaker for Azure Form Recognizer"""
    return circuit_breaker(
        "form_recognizer",
        failure_threshold=3,
        timeout=30.0
    )(func)


def openai_circuit_breaker(func: Callable) -> Callable:
    """Circuit breaker for Azure OpenAI"""
    return circuit_breaker(
        "openai",
        failure_threshold=3,
        timeout=30.0
    )(func)


def database_circuit_breaker(func: Callable) -> Callable:
    """Circuit breaker for database"""
    return circuit_breaker(
        "database",
        failure_threshold=5,
        timeout=60.0
    )(func)


def redis_circuit_breaker(func: Callable) -> Callable:
    """Circuit breaker for Redis"""
    return circuit_breaker(
        "redis",
        failure_threshold=3,
        timeout=30.0
    )(func)

