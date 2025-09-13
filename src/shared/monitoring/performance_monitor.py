"""
Performance Monitoring Service
Tracks and optimizes system performance metrics
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps
import psutil
import gc

from ..cache.redis_cache import cache_service

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None

class PerformanceMonitor:
    """Advanced performance monitoring and optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics: List[PerformanceMetric] = []
        self.start_time = time.time()
        
    async def track_function_performance(self, func_name: str, execution_time: float, 
                                       memory_usage: float = None, tags: Dict[str, str] = None):
        """Track function performance metrics"""
        try:
            metric = PerformanceMetric(
                name=f"function.{func_name}",
                value=execution_time,
                timestamp=datetime.utcnow(),
                tags=tags or {}
            )
            
            # Store in memory
            self.metrics.append(metric)
            
            # Store in cache for real-time monitoring
            await cache_service.set(
                f"perf_metric:{func_name}:{int(time.time())}",
                {
                    "execution_time": execution_time,
                    "memory_usage": memory_usage,
                    "timestamp": datetime.utcnow().isoformat(),
                    "tags": tags or {}
                },
                ttl=3600  # 1 hour
            )
            
            # Keep only last 1000 metrics in memory
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
                
        except Exception as e:
            self.logger.error(f"Error tracking performance metric: {str(e)}")
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Process count
            process_count = len(psutil.pids())
            
            # Uptime
            uptime_seconds = time.time() - self.start_time
            uptime_hours = uptime_seconds / 3600
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "used_gb": round(memory_used_gb, 2),
                    "total_gb": round(memory_total_gb, 2),
                    "available_gb": round((memory.total - memory.used) / (1024**3), 2)
                },
                "disk": {
                    "usage_percent": disk_percent,
                    "used_gb": round(disk_used_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "free_gb": round((disk.total - disk.used) / (1024**3), 2)
                },
                "processes": {
                    "count": process_count,
                    "python_count": len([p for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()])
                },
                "uptime": {
                    "seconds": uptime_seconds,
                    "hours": round(uptime_hours, 2)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the last hour"""
        try:
            now = datetime.utcnow()
            one_hour_ago = now - timedelta(hours=1)
            
            # Filter metrics from last hour
            recent_metrics = [
                m for m in self.metrics 
                if m.timestamp >= one_hour_ago
            ]
            
            if not recent_metrics:
                return {"message": "No performance data available"}
            
            # Group by function name
            function_metrics = {}
            for metric in recent_metrics:
                func_name = metric.name.replace("function.", "")
                if func_name not in function_metrics:
                    function_metrics[func_name] = []
                function_metrics[func_name].append(metric.value)
            
            # Calculate statistics
            summary = {}
            for func_name, values in function_metrics.items():
                summary[func_name] = {
                    "count": len(values),
                    "avg_execution_time": round(sum(values) / len(values), 4),
                    "min_execution_time": round(min(values), 4),
                    "max_execution_time": round(max(values), 4),
                    "total_execution_time": round(sum(values), 4)
                }
            
            return {
                "period": "last_hour",
                "total_functions_called": len(function_metrics),
                "total_calls": len(recent_metrics),
                "functions": summary
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {str(e)}")
            return {}
    
    async def optimize_memory(self):
        """Optimize memory usage"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory before and after
            memory_before = psutil.virtual_memory().used / (1024**3)
            
            # Clear old metrics
            if len(self.metrics) > 500:
                self.metrics = self.metrics[-500:]
            
            memory_after = psutil.virtual_memory().used / (1024**3)
            memory_freed = memory_before - memory_after
            
            self.logger.info(f"Memory optimization: freed {memory_freed:.2f} GB, collected {collected} objects")
            
            return {
                "memory_freed_gb": round(memory_freed, 2),
                "objects_collected": collected,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing memory: {str(e)}")
            return {}

def monitor_performance(func_name: str = None, tags: Dict[str, str] = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
                
                execution_time = end_time - start_time
                memory_usage = end_memory - start_memory
                
                # Track performance
                monitor = PerformanceMonitor()
                await monitor.track_function_performance(
                    func_name or func.__name__,
                    execution_time,
                    memory_usage,
                    tags
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
                
                execution_time = end_time - start_time
                memory_usage = end_memory - start_memory
                
                # Track performance (async)
                monitor = PerformanceMonitor()
                asyncio.create_task(monitor.track_function_performance(
                    func_name or func.__name__,
                    execution_time,
                    memory_usage,
                    tags
                ))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Global performance monitor instance
performance_monitor = PerformanceMonitor()