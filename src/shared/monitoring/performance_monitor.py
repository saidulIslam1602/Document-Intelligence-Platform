"""
Production Performance Monitoring and Metrics Collection
Tracks request latency, throughput, error rates, and resource usage
"""

import time
import logging
import asyncio
from typing import Optional, Callable
from functools import wraps
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import psutil

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Centralized metrics collection for performance monitoring
    
    Tracks:
    - Request latency (p50, p95, p99)
    - Throughput (requests/second)
    - Error rates (4xx, 5xx)
    - Resource usage (CPU, memory)
    - Database query times
    - Cache hit rates
    """
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0
        self.latencies = []
        self.start_time = time.time()
        
        # Track by endpoint
        self.endpoint_metrics = {}
        
        # Resource usage
        self.cpu_percent = 0
        self.memory_percent = 0
    
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency: float,
    ):
        """Record request metrics"""
        self.request_count += 1
        self.total_latency += latency
        self.latencies.append(latency)
        
        # Keep only last 1000 latencies for memory efficiency
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]
        
        if status_code >= 400:
            self.error_count += 1
        
        # Track per-endpoint metrics
        endpoint_key = f"{method}:{path}"
        if endpoint_key not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint_key] = {
                'count': 0,
                'errors': 0,
                'total_latency': 0,
            }
        
        self.endpoint_metrics[endpoint_key]['count'] += 1
        self.endpoint_metrics[endpoint_key]['total_latency'] += latency
        
        if status_code >= 400:
            self.endpoint_metrics[endpoint_key]['errors'] += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics snapshot"""
        uptime = time.time() - self.start_time
        
        # Calculate percentiles
        sorted_latencies = sorted(self.latencies) if self.latencies else [0]
        p50_index = int(len(sorted_latencies) * 0.50)
        p95_index = int(len(sorted_latencies) * 0.95)
        p99_index = int(len(sorted_latencies) * 0.99)
        
        # Update resource usage
        self.cpu_percent = psutil.cpu_percent(interval=0.1)
        self.memory_percent = psutil.virtual_memory().percent
        
        return {
            'uptime_seconds': round(uptime, 2),
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': round(self.error_count / max(self.request_count, 1), 4),
            'requests_per_second': round(self.request_count / uptime, 2),
            'latency': {
                'avg_ms': round(self.total_latency / max(self.request_count, 1) * 1000, 2),
                'p50_ms': round(sorted_latencies[p50_index] * 1000, 2),
                'p95_ms': round(sorted_latencies[p95_index] * 1000, 2),
                'p99_ms': round(sorted_latencies[p99_index] * 1000, 2),
            },
            'resources': {
                'cpu_percent': round(self.cpu_percent, 2),
                'memory_percent': round(self.memory_percent, 2),
                'memory_mb': round(psutil.virtual_memory().used / 1024 / 1024, 2),
            },
            'top_endpoints': self._get_top_endpoints(),
        }
    
    def _get_top_endpoints(self, limit: int = 10) -> list:
        """Get top endpoints by request count"""
        sorted_endpoints = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:limit]
        
        return [
            {
                'endpoint': endpoint,
                'count': metrics['count'],
                'avg_latency_ms': round(metrics['total_latency'] / metrics['count'] * 1000, 2),
                'error_rate': round(metrics['errors'] / metrics['count'], 4),
            }
            for endpoint, metrics in sorted_endpoints
        ]
    
    def reset(self):
        """Reset all metrics (useful for testing)"""
        self.__init__()


# Global metrics instance
metrics = PerformanceMetrics()


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic performance monitoring
    
    Usage:
        app.add_middleware(PerformanceMonitorMiddleware)
    """
    
    def __init__(self, app: ASGIApp, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Add request ID for tracing
        request_id = request.headers.get('X-Request-ID', str(time.time()))
        
        try:
            response = await call_next(request)
            latency = time.time() - start_time
            
            # Record metrics
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency=latency,
            )
            
            # Log slow requests
            if latency > self.slow_request_threshold:
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path} "
                    f"took {latency:.2f}s (threshold: {self.slow_request_threshold}s)"
                )
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{latency:.3f}s"
            response.headers['X-Request-ID'] = request_id
            
            return response
        
        except Exception as e:
            latency = time.time() - start_time
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                latency=latency,
            )
            logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
            raise


def monitor_performance(threshold: float = 1.0):
    """
    Decorator to monitor individual function performance
    
    Usage:
        @monitor_performance(threshold=0.5)
        async def expensive_operation():
            # Your code here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                latency = time.time() - start_time
                
                if latency > threshold:
                    logger.warning(
                        f"Slow function: {func.__name__} took {latency:.2f}s "
                        f"(threshold: {threshold}s)"
                    )
                
                return result
            except Exception as e:
                latency = time.time() - start_time
                logger.error(f"Function {func.__name__} failed after {latency:.2f}s: {str(e)}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                latency = time.time() - start_time
                
                if latency > threshold:
                    logger.warning(
                        f"Slow function: {func.__name__} took {latency:.2f}s "
                        f"(threshold: {threshold}s)"
                    )
                
                return result
            except Exception as e:
                latency = time.time() - start_time
                logger.error(f"Function {func.__name__} failed after {latency:.2f}s: {str(e)}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Database query monitoring
class QueryMonitor:
    """Monitor database query performance"""
    
    def __init__(self):
        self.queries = []
        self.slow_query_threshold = 0.1  # 100ms
    
    def record_query(self, query: str, duration: float, rows: int = 0):
        """Record query execution"""
        self.queries.append({
            'query': query[:200],  # Truncate long queries
            'duration': duration,
            'rows': rows,
            'timestamp': datetime.utcnow().isoformat(),
        })
        
        # Keep only last 100 queries
        if len(self.queries) > 100:
            self.queries = self.queries[-100:]
        
        # Log slow queries
        if duration > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected ({duration:.3f}s): {query[:100]}..."
            )
    
    def get_slow_queries(self, limit: int = 10) -> list:
        """Get slowest queries"""
        return sorted(
            self.queries,
            key=lambda x: x['duration'],
            reverse=True
        )[:limit]


query_monitor = QueryMonitor()


# Cost optimization tracking
class CostTracker:
    """Track cloud resource costs for optimization"""
    
    def __init__(self):
        self.api_calls = {
            'openai': 0,
            'form_recognizer': 0,
            'cognitive_search': 0,
        }
        
        # Estimated costs per call (update with actual pricing)
        self.cost_per_call = {
            'openai': 0.002,  # $0.002 per call
            'form_recognizer': 0.01,  # $0.01 per page
            'cognitive_search': 0.001,  # $0.001 per query
        }
    
    def record_api_call(self, service: str, count: int = 1):
        """Record API call for cost tracking"""
        if service in self.api_calls:
            self.api_calls[service] += count
    
    def get_estimated_costs(self) -> dict:
        """Calculate estimated costs"""
        return {
            'api_calls': self.api_calls,
            'estimated_costs': {
                service: round(count * self.cost_per_call.get(service, 0), 2)
                for service, count in self.api_calls.items()
            },
            'total_estimated': round(
                sum(
                    count * self.cost_per_call.get(service, 0)
                    for service, count in self.api_calls.items()
                ),
                2
            ),
        }


cost_tracker = CostTracker()
