"""
Health Check System
Comprehensive health monitoring for all service dependencies
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import httpx
from ..config.enhanced_settings import get_settings

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enum"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DependencyCheck:
    """Base class for dependency health checks"""
    
    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
    
    async def check(self) -> Dict[str, Any]:
        """
        Perform health check
        
        Returns:
            Dict with status, response_time_ms, message, and optional details
        """
        raise NotImplementedError


class HTTPDependencyCheck(DependencyCheck):
    """Health check for HTTP dependencies"""
    
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        timeout: float = 5.0,
        expected_status: int = 200,
        critical: bool = True
    ):
        super().__init__(name, critical)
        self.url = url
        self.method = method
        self.timeout = timeout
        self.expected_status = expected_status
    
    async def check(self) -> Dict[str, Any]:
        """Check HTTP endpoint health"""
        start_time = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.method == "GET":
                    response = await client.get(self.url)
                elif self.method == "POST":
                    response = await client.post(self.url)
                elif self.method == "HEAD":
                    response = await client.head(self.url)
                else:
                    raise ValueError(f"Unsupported method: {self.method}")
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status_code == self.expected_status:
                    return {
                        "status": HealthStatus.HEALTHY,
                        "response_time_ms": round(response_time, 2),
                        "message": f"{self.name} is healthy",
                        "details": {
                            "status_code": response.status_code,
                            "url": self.url
                        }
                    }
                else:
                    return {
                        "status": HealthStatus.DEGRADED,
                        "response_time_ms": round(response_time, 2),
                        "message": f"{self.name} returned unexpected status",
                        "details": {
                            "status_code": response.status_code,
                            "expected": self.expected_status,
                            "url": self.url
                        }
                    }
                    
        except httpx.TimeoutException:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} request timed out",
                "details": {"url": self.url, "timeout": self.timeout}
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} health check failed: {str(e)}",
                "details": {"url": self.url, "error": str(e)}
            }


class RedisDependencyCheck(DependencyCheck):
    """Health check for Redis"""
    
    def __init__(self, name: str = "Redis", critical: bool = True):
        super().__init__(name, critical)
    
    async def check(self) -> Dict[str, Any]:
        """Check Redis health"""
        start_time = datetime.now()
        settings = get_settings()
        
        try:
            import redis.asyncio as aioredis
            
            client = await aioredis.from_url(
                settings.get_redis_url(),
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Ping Redis
            await client.ping()
            
            # Get info
            info = await client.info()
            
            await client.close()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} is healthy",
                "details": {
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human")
                }
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} health check failed: {str(e)}",
                "details": {"error": str(e)}
            }


class DatabaseDependencyCheck(DependencyCheck):
    """Health check for SQL Database"""
    
    def __init__(self, name: str = "SQL Database", critical: bool = True):
        super().__init__(name, critical)
    
    async def check(self) -> Dict[str, Any]:
        """Check database health"""
        start_time = datetime.now()
        settings = get_settings()
        
        try:
            import pyodbc
            
            # Use asyncio to run blocking ODBC call
            def check_db():
                conn = pyodbc.connect(
                    settings.database.connection_string,
                    timeout=5
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
            
            await asyncio.to_thread(check_db)
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} is healthy",
                "details": {
                    "server": settings.database.server_name or "configured",
                    "database": settings.database.database_name or "configured"
                }
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} health check failed: {str(e)}",
                "details": {"error": str(e)}
            }


class AzureServiceDependencyCheck(DependencyCheck):
    """Health check for Azure services (Form Recognizer, OpenAI, etc.)"""
    
    def __init__(
        self,
        name: str,
        endpoint: str,
        api_key: Optional[str] = None,
        critical: bool = True
    ):
        super().__init__(name, critical)
        self.endpoint = endpoint
        self.api_key = api_key
    
    async def check(self) -> Dict[str, Any]:
        """Check Azure service health"""
        start_time = datetime.now()
        
        try:
            headers = {}
            if self.api_key:
                headers["Ocp-Apim-Subscription-Key"] = self.api_key
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try a simple GET or OPTIONS request
                response = await client.get(
                    self.endpoint,
                    headers=headers,
                    follow_redirects=True
                )
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Azure services typically return 200, 400, or 401 for health
                if response.status_code in (200, 400, 401):
                    return {
                        "status": HealthStatus.HEALTHY,
                        "response_time_ms": round(response_time, 2),
                        "message": f"{self.name} is reachable",
                        "details": {
                            "endpoint": self.endpoint,
                            "status_code": response.status_code
                        }
                    }
                else:
                    return {
                        "status": HealthStatus.DEGRADED,
                        "response_time_ms": round(response_time, 2),
                        "message": f"{self.name} returned unexpected status",
                        "details": {
                            "endpoint": self.endpoint,
                            "status_code": response.status_code
                        }
                    }
                    
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": round(response_time, 2),
                "message": f"{self.name} health check failed: {str(e)}",
                "details": {"endpoint": self.endpoint, "error": str(e)}
            }


class HealthCheckService:
    """Centralized health check service"""
    
    def __init__(self):
        self.dependencies: List[DependencyCheck] = []
        self.settings = get_settings()
        self._setup_default_checks()
    
    def _setup_default_checks(self):
        """Setup default health checks for common dependencies"""
        
        # Redis
        self.dependencies.append(
            RedisDependencyCheck("Redis", critical=True)
        )
        
        # SQL Database
        self.dependencies.append(
            DatabaseDependencyCheck("SQL Database", critical=True)
        )
        
        # Azure Form Recognizer
        if hasattr(self.settings, 'form_recognizer') and self.settings.form_recognizer.endpoint:
            self.dependencies.append(
                AzureServiceDependencyCheck(
                    "Form Recognizer",
                    self.settings.form_recognizer.endpoint,
                    self.settings.form_recognizer.key,
                    critical=True
                )
            )
        
        # Azure OpenAI
        if hasattr(self.settings, 'openai') and self.settings.openai.endpoint:
            self.dependencies.append(
                AzureServiceDependencyCheck(
                    "Azure OpenAI",
                    self.settings.openai.endpoint,
                    self.settings.openai.api_key,
                    critical=True
                )
            )
        
        # Internal Microservices
        services = [
            ("Document Ingestion", "document_ingestion_url", "/health"),
            ("AI Processing", "ai_processing_url", "/health"),
            ("Analytics", "analytics_url", "/health"),
            ("AI Chat", "ai_chat_url", "/health"),
            ("MCP Server", "mcp_server_url", "/health"),
        ]
        
        for service_name, url_attr, path in services:
            if hasattr(self.settings, url_attr):
                url = getattr(self.settings, url_attr)
                self.dependencies.append(
                    HTTPDependencyCheck(
                        service_name,
                        f"{url}{path}",
                        critical=False  # Internal services not critical for health
                    )
                )
    
    def add_dependency(self, dependency: DependencyCheck):
        """Add a custom dependency check"""
        self.dependencies.append(dependency)
    
    async def check_dependency(self, dependency: DependencyCheck) -> Dict[str, Any]:
        """Check a single dependency"""
        try:
            result = await dependency.check()
            return {
                "name": dependency.name,
                "critical": dependency.critical,
                **result
            }
        except Exception as e:
            logger.error(f"Health check failed for {dependency.name}: {e}")
            return {
                "name": dependency.name,
                "critical": dependency.critical,
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": 0,
                "message": f"Health check error: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def check_all(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Check all dependencies
        
        Returns:
            Dict with overall status and individual dependency results
        """
        start_time = datetime.now()
        
        # Run all checks concurrently with timeout
        try:
            tasks = [
                self.check_dependency(dep)
                for dep in self.dependencies
            ]
            
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # Process results
            dependency_results = []
            critical_unhealthy = []
            non_critical_unhealthy = []
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Health check exception: {result}")
                    continue
                
                dependency_results.append(result)
                
                if result["status"] == HealthStatus.UNHEALTHY:
                    if result["critical"]:
                        critical_unhealthy.append(result["name"])
                    else:
                        non_critical_unhealthy.append(result["name"])
            
            # Determine overall status
            if critical_unhealthy:
                overall_status = HealthStatus.UNHEALTHY
                message = f"Critical dependencies unhealthy: {', '.join(critical_unhealthy)}"
            elif non_critical_unhealthy:
                overall_status = HealthStatus.DEGRADED
                message = f"Non-critical dependencies unhealthy: {', '.join(non_critical_unhealthy)}"
            else:
                overall_status = HealthStatus.HEALTHY
                message = "All dependencies healthy"
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": overall_status,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": round(total_time, 2),
                "dependencies": dependency_results,
                "summary": {
                    "total": len(dependency_results),
                    "healthy": len([r for r in dependency_results if r["status"] == HealthStatus.HEALTHY]),
                    "degraded": len([r for r in dependency_results if r["status"] == HealthStatus.DEGRADED]),
                    "unhealthy": len([r for r in dependency_results if r["status"] == HealthStatus.UNHEALTHY]),
                    "critical_unhealthy": len(critical_unhealthy),
                    "non_critical_unhealthy": len(non_critical_unhealthy)
                }
            }
            
        except asyncio.TimeoutError:
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Health check timed out after {timeout}s",
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": round(total_time, 2),
                "dependencies": [],
                "summary": {}
            }
    
    async def check_liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - is the service running?
        
        Returns:
            Simple status indicating if service is alive
        """
        return {
            "status": HealthStatus.HEALTHY,
            "message": "Service is alive",
            "timestamp": datetime.now().isoformat()
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - is the service ready to serve traffic?
        
        Returns:
            Status indicating if service is ready (all critical dependencies healthy)
        """
        health = await self.check_all(timeout=10.0)
        
        # Check if critical dependencies are healthy
        critical_unhealthy = [
            dep for dep in health.get("dependencies", [])
            if dep["critical"] and dep["status"] == HealthStatus.UNHEALTHY
        ]
        
        if critical_unhealthy:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Not ready: {len(critical_unhealthy)} critical dependencies unhealthy",
                "timestamp": datetime.now().isoformat(),
                "critical_dependencies": [dep["name"] for dep in critical_unhealthy]
            }
        else:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Service is ready",
                "timestamp": datetime.now().isoformat()
            }


# Global health check service instance
_health_service: Optional[HealthCheckService] = None


def get_health_service() -> HealthCheckService:
    """Get or create health check service singleton"""
    global _health_service
    if _health_service is None:
        _health_service = HealthCheckService()
    return _health_service

