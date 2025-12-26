"""
Health Check and Monitoring System - Production-Grade Service Health Management

This module implements a comprehensive health check system for monitoring service
dependencies, providing deep visibility into system health for operations, monitoring,
and automated recovery.

Overview:
---------
In distributed systems and microservices architectures, health checks are critical for:
1. **Load Balancer Routing**: Route traffic only to healthy instances
2. **Orchestration**: Kubernetes/Docker uses health checks for container management
3. **Alerting**: Trigger alerts when dependencies fail
4. **Debugging**: Quickly identify which components are failing
5. **SLA Monitoring**: Track uptime and reliability metrics
6. **Auto-Recovery**: Restart unhealthy services automatically

This implementation provides three types of health checks:
- **Liveness**: Is the service running? (for container orchestration)
- **Readiness**: Is the service ready to accept traffic? (for load balancers)
- **Dependency**: Are all dependencies healthy? (for operational insights)

Health Check Types:
-------------------

1. **Liveness Probe**
   - Purpose: Determine if service should be restarted
   - Question: "Is the application process running?"
   - Success: Service is alive
   - Failure: Container should be restarted
   - Kubernetes: `livenessProbe`
   - Typical Check: Simple endpoint that always returns 200

2. **Readiness Probe**
   - Purpose: Determine if service can handle requests
   - Question: "Is the service ready to serve traffic?"
   - Success: Can route traffic to this instance
   - Failure: Remove from load balancer pool temporarily
   - Kubernetes: `readinessProbe`
   - Typical Check: Critical dependencies are healthy

3. **Dependency Health Check**
   - Purpose: Monitor all dependencies comprehensively
   - Question: "What is the health of each dependency?"
   - Success: All dependencies operational
   - Failure: Specific dependencies identified
   - Monitoring: Prometheus, Grafana, Azure Monitor
   - Typical Check: Test all connections (DB, cache, APIs)

Health Status States:
---------------------

```
HEALTHY (✅)
├─ All critical dependencies operational
├─ Response times within SLA
├─ No errors detected
└─ Ready to serve traffic

DEGRADED (⚠️)
├─ Non-critical dependencies failing
├─ Service still operational
├─ Reduced functionality
└─ Should alert but not fail

UNHEALTHY (❌)
├─ Critical dependencies failing
├─ Cannot serve traffic reliably
├─ Should be removed from load balancer
└─ Requires immediate attention

UNKNOWN (❓)
├─ Health check could not complete
├─ Timeout or exception occurred
└─ Treat as unhealthy for safety
```

Critical vs Non-Critical Dependencies:
---------------------------------------

**Critical Dependencies** (service cannot function without):
- Primary database (SQL Server, Azure SQL)
- Cache layer (Redis) - if mandatory for performance
- Authentication service
- Core external APIs

**Non-Critical Dependencies** (service can degrade gracefully):
- Analytics database (can queue events)
- Monitoring services (can buffer metrics)
- Optional integrations
- Background job queues

Architecture:
-------------

```
HealthCheckService (Coordinator)
    ├─ DependencyCheck (Base Class)
    │   ├─ HTTPDependencyCheck (Microservices, REST APIs)
    │   ├─ RedisDependencyCheck (Cache)
    │   ├─ DatabaseDependencyCheck (SQL Database)
    │   └─ AzureServiceDependencyCheck (Azure AI services)
    │
    ├─ check_liveness() → Simple "alive" check
    ├─ check_readiness() → Check critical dependencies
    └─ check_all() → Comprehensive dependency health
```

Dependency Check Implementations:
----------------------------------

1. **HTTPDependencyCheck**
   - Checks: Microservices, REST APIs, webhooks
   - Method: GET/POST/HEAD request
   - Timeout: Configurable (default 5s)
   - Success: Expected HTTP status (usually 200)
   - Use Case: Internal microservices, external APIs

2. **RedisDependencyCheck**
   - Checks: Redis cache server
   - Method: PING command
   - Success: PONG response
   - Details: Version, memory usage, connected clients
   - Use Case: Session storage, rate limiting, caching

3. **DatabaseDependencyCheck**
   - Checks: SQL Database (Azure SQL, SQL Server)
   - Method: SELECT 1 query
   - Success: Query returns result
   - Details: Server name, database name
   - Use Case: Primary data store

4. **AzureServiceDependencyCheck**
   - Checks: Azure AI services (Form Recognizer, OpenAI, etc.)
   - Method: GET request to endpoint
   - Success: Service responds (200, 400, 401 acceptable)
   - Use Case: Azure Cognitive Services

Response Format:
----------------

```json
{
  "status": "healthy|degraded|unhealthy|unknown",
  "message": "Human-readable status description",
  "timestamp": "2024-01-15T10:30:00Z",
  "response_time_ms": 123.45,
  "dependencies": [
    {
      "name": "SQL Database",
      "critical": true,
      "status": "healthy",
      "response_time_ms": 12.34,
      "message": "SQL Database is healthy",
      "details": {
        "server": "prod-db.database.windows.net",
        "database": "docdb"
      }
    },
    {
      "name": "Redis",
      "critical": true,
      "status": "healthy",
      "response_time_ms": 5.67,
      "message": "Redis is healthy",
      "details": {
        "version": "7.0.5",
        "connected_clients": 42,
        "used_memory_human": "2.5M"
      }
    }
  ],
  "summary": {
    "total": 10,
    "healthy": 8,
    "degraded": 1,
    "unhealthy": 1,
    "critical_unhealthy": 0,
    "non_critical_unhealthy": 1
  }
}
```

Kubernetes Integration:
-----------------------

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: document-intelligence
    image: docintel:latest
    
    # Liveness Probe: Restart if unhealthy
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    
    # Readiness Probe: Route traffic when ready
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 5
      failureThreshold: 3
    
    # Startup Probe: Allow slow startup
    startupProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 0
      periodSeconds: 5
      failureThreshold: 30  # 150s max startup time
```

FastAPI Integration:
--------------------

```python
from fastapi import FastAPI, status
from src.shared.health.health_check import get_health_service

app = FastAPI()
health_service = get_health_service()

@app.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    \"\"\"Liveness probe for Kubernetes\"\"\"
    result = await health_service.check_liveness()
    return result

@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe():
    \"\"\"Readiness probe for Kubernetes\"\"\"
    result = await health_service.check_readiness()
    if result["status"] != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result
        )
    return result

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    \"\"\"Comprehensive health check for monitoring\"\"\"
    result = await health_service.check_all()
    if result["status"] == "unhealthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result
        )
    return result
```

Monitoring and Alerting:
------------------------

**Prometheus Metrics**:
```python
from prometheus_client import Gauge, Histogram

health_status = Gauge(
    'service_health_status',
    'Health status (0=healthy, 1=degraded, 2=unhealthy)',
    ['service_name']
)

dependency_health = Gauge(
    'dependency_health_status',
    'Dependency health status',
    ['dependency_name', 'critical']
)

health_check_duration = Histogram(
    'health_check_duration_seconds',
    'Health check duration',
    ['check_type']
)
```

**Alert Rules**:
```
ALERT ServiceUnhealthy
  IF service_health_status == 2
  FOR 1m
  LABELS { severity="critical" }
  ANNOTATIONS {
    summary="Service {{ $labels.service_name }} is unhealthy",
    description="Critical dependencies are failing"
  }

ALERT ServiceDegraded
  IF service_health_status == 1
  FOR 5m
  LABELS { severity="warning" }
  ANNOTATIONS {
    summary="Service {{ $labels.service_name }} is degraded",
    description="Non-critical dependencies are failing"
  }
```

Custom Dependency Checks:
--------------------------

```python
from src.shared.health.health_check import DependencyCheck, get_health_service

class CustomDependencyCheck(DependencyCheck):
    async def check(self) -> Dict[str, Any]:
        try:
            # Your custom health check logic
            await my_custom_service.ping()
            
            return {
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 10.0,
                "message": "Custom service is healthy",
                "details": {"version": "1.0"}
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "response_time_ms": 0,
                "message": f"Custom service failed: {e}",
                "details": {"error": str(e)}
            }

# Register custom check
health_service = get_health_service()
health_service.add_dependency(
    CustomDependencyCheck("My Service", critical=True)
)
```

Best Practices:
---------------

1. **Fast Checks**: Health checks should complete in < 5s
2. **Timeouts**: Always set timeouts on dependency checks
3. **Lightweight**: Don't perform expensive operations
4. **Critical Flag**: Mark dependencies as critical/non-critical appropriately
5. **Caching**: Cache health results (but not too long, 30-60s max)
6. **Concurrency**: Run checks in parallel for speed
7. **Logging**: Log state changes, not every check
8. **Retries**: Don't retry in health checks (let orchestrator handle)
9. **Details**: Include actionable information in failure details
10. **Endpoints**: Separate liveness, readiness, and full health checks

Common Pitfalls:
----------------

❌ Health check is slow (> 10s) → Times out in Kubernetes
❌ Health check does expensive work → Overloads service
❌ All dependencies critical → Service always unhealthy
❌ No timeout on checks → Health check hangs
❌ Retries in health check → Slow and unpredictable
❌ Same endpoint for liveness and readiness → Confuses orchestrator
❌ No caching → Health check overhead too high
❌ Not monitoring health check failures → Unaware of outages

Performance Considerations:
---------------------------

- **Parallel Execution**: All checks run concurrently
- **Timeout**: Global timeout prevents hanging (default 30s)
- **Caching**: Consider caching results for 30-60s under high load
- **Response Time**: Aim for < 1s for readiness, < 5s for full health
- **Resource Usage**: Minimal (< 50MB memory, < 1% CPU)

Testing:
--------

```python
import pytest
from src.shared.health.health_check import get_health_service

@pytest.mark.asyncio
async def test_liveness_always_healthy():
    health_service = get_health_service()
    result = await health_service.check_liveness()
    assert result["status"] == "healthy"

@pytest.mark.asyncio
async def test_readiness_with_unhealthy_critical_dependency():
    # Mock critical dependency as unhealthy
    result = await health_service.check_readiness()
    assert result["status"] == "unhealthy"

@pytest.mark.asyncio
async def test_full_health_check():
    health_service = get_health_service()
    result = await health_service.check_all(timeout=10.0)
    assert "status" in result
    assert "dependencies" in result
    assert "summary" in result
```

References:
-----------
- Kubernetes Health Checks: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Google SRE Book - Health Checking: https://sre.google/sre-book/monitoring-distributed-systems/
- Azure Health Checks: https://docs.microsoft.com/azure/architecture/patterns/health-endpoint-monitoring
- Martin Fowler - Health Checks: https://martinfowler.com/articles/microservice-trade-offs.html
- Prometheus Best Practices: https://prometheus.io/docs/practices/naming/

Industry Standards:
-------------------
- **HTTP 200**: Service healthy
- **HTTP 503**: Service unavailable (unhealthy/degraded)
- **Response Format**: JSON with status, message, timestamp
- **Endpoint Paths**: `/health/live`, `/health/ready`, `/health` (or `/healthz`)
- **Timeout**: 5-10s maximum
- **Frequency**: Every 10-30s for readiness, every 30s for liveness

Author: Document Intelligence Platform Team
Version: 2.0.0
Module: Health Monitoring and Service Observability
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
    """
    Centralized Health Check Service - Comprehensive Dependency Monitoring
    
    This service orchestrates health checks across all system dependencies, providing
    a unified interface for liveness, readiness, and full health monitoring.
    
    Features:
    ---------
    - **Parallel Execution**: All checks run concurrently for speed
    - **Timeout Protection**: Global timeout prevents hanging checks
    - **Critical/Non-Critical**: Differentiate failure impact
    - **Default Checks**: Auto-discovers common dependencies
    - **Extensible**: Add custom dependency checks
    - **Kubernetes Ready**: Provides liveness and readiness probes
    - **Monitoring Ready**: Structured output for metrics export
    
    Architecture:
    -------------
    ```
    HealthCheckService
    ├─ Dependencies Registry
    │   ├─ Critical Dependencies (affect service readiness)
    │   │   ├─ SQL Database
    │   │   ├─ Redis Cache
    │   │   ├─ Azure Form Recognizer
    │   │   └─ Azure OpenAI
    │   │
    │   └─ Non-Critical Dependencies (degrade gracefully)
    │       ├─ Internal Microservices
    │       ├─ Analytics Services
    │       └─ Optional Integrations
    │
    ├─ Check Methods
    │   ├─ check_liveness() → "Is service alive?"
    │   ├─ check_readiness() → "Can handle traffic?"
    │   └─ check_all() → "What is health of all dependencies?"
    │
    └─ Dependency Management
        ├─ _setup_default_checks() → Auto-discover dependencies
        └─ add_dependency() → Register custom checks
    ```
    
    Health Decision Logic:
    ----------------------
    ```
    Overall Status = f(Critical Dependencies, Non-Critical Dependencies)
    
    IF any critical dependency is UNHEALTHY:
        → Overall Status = UNHEALTHY (cannot serve traffic)
    
    ELIF any non-critical dependency is UNHEALTHY:
        → Overall Status = DEGRADED (can serve traffic, reduced functionality)
    
    ELSE:
        → Overall Status = HEALTHY (all systems operational)
    ```
    
    Default Dependency Checks:
    --------------------------
    
    **Always Registered**:
    1. Redis Cache (critical)
    2. SQL Database (critical)
    
    **Conditionally Registered** (if configured):
    3. Azure Form Recognizer (critical) - if endpoint configured
    4. Azure OpenAI (critical) - if endpoint configured
    5. Document Ingestion Service (non-critical)
    6. AI Processing Service (non-critical)
    7. Analytics Service (non-critical)
    8. AI Chat Service (non-critical)
    9. MCP Server (non-critical)
    
    Note: Internal microservices are non-critical because they can be
    temporarily unavailable without affecting core service functionality.
    
    Usage Examples:
    ---------------
    
    **Example 1: Basic Health Check**
    ```python
    from src.shared.health.health_check import get_health_service
    
    health_service = get_health_service()
    result = await health_service.check_all()
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    for dep in result['dependencies']:
        print(f"  {dep['name']}: {dep['status']} ({dep['response_time_ms']}ms)")
    ```
    
    **Example 2: Kubernetes Integration**
    ```python
    @app.get("/health/live")
    async def liveness():
        \"\"\"Liveness probe - is service running?\"\"\"
        health_service = get_health_service()
        return await health_service.check_liveness()
    
    @app.get("/health/ready")
    async def readiness():
        \"\"\"Readiness probe - can service handle traffic?\"\"\"
        health_service = get_health_service()
        result = await health_service.check_readiness()
        
        if result["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail=result["message"]
            )
        return result
    
    @app.get("/health")
    async def health():
        \"\"\"Full health check - detailed dependency status\"\"\"
        health_service = get_health_service()
        result = await health_service.check_all()
        
        if result["status"] == "unhealthy":
            raise HTTPException(
                status_code=503,
                detail=result
            )
        return result
    ```
    
    **Example 3: Custom Dependency Check**
    ```python
    from src.shared.health.health_check import (
        get_health_service,
        DependencyCheck,
        HealthStatus
    )
    
    class MongoDBCheck(DependencyCheck):
        async def check(self) -> Dict[str, Any]:
            try:
                await mongo_client.admin.command('ping')
                return {
                    "status": HealthStatus.HEALTHY,
                    "response_time_ms": 5.0,
                    "message": "MongoDB is healthy"
                }
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "response_time_ms": 0,
                    "message": f"MongoDB check failed: {e}"
                }
    
    # Register custom check
    health_service = get_health_service()
    health_service.add_dependency(
        MongoDBCheck("MongoDB", critical=True)
    )
    ```
    
    **Example 4: Monitoring Integration**
    ```python
    from prometheus_client import Gauge
    
    health_gauge = Gauge(
        'service_health_status',
        'Overall service health',
        ['service']
    )
    
    async def update_health_metrics():
        health_service = get_health_service()
        result = await health_service.check_all()
        
        # Map status to numeric value
        status_map = {
            "healthy": 0,
            "degraded": 1,
            "unhealthy": 2,
            "unknown": 3
        }
        
        health_gauge.labels(service="document-intelligence").set(
            status_map[result["status"]]
        )
    ```
    
    Performance Characteristics:
    ----------------------------
    - **check_liveness()**: < 1ms (no I/O, just confirms service is running)
    - **check_readiness()**: 100-500ms (checks critical dependencies only)
    - **check_all()**: 500ms-5s (checks all dependencies in parallel)
    - **Memory**: ~1KB per registered dependency
    - **Concurrency**: Thread-safe (singleton pattern)
    
    Configuration:
    --------------
    Dependencies are auto-discovered from settings.py:
    
    ```python
    # settings.py
    class Settings:
        redis_host: str = "localhost"
        redis_port: int = 6379
        database_connection_string: str = "..."
        form_recognizer_endpoint: str = "..."
        openai_endpoint: str = "..."
        # ... etc
    ```
    
    The service automatically creates health checks for any configured endpoints.
    
    Timeout Behavior:
    -----------------
    - Default timeout: 30s for full health check
    - Readiness timeout: 10s (faster for load balancer decisions)
    - Per-check timeout: 5s (prevents individual checks from hanging)
    
    If timeout is exceeded:
    - Status: UNHEALTHY
    - Message: "Health check timed out after Xs"
    - No dependency results returned
    - Kubernetes/load balancer should treat as unhealthy
    
    Error Handling:
    ---------------
    - Individual check failures don't crash the service
    - Exceptions are caught and returned as UNHEALTHY status
    - Errors are logged for debugging
    - Partial results are always returned
    
    Best Practices:
    ---------------
    1. **Mark Dependencies Correctly**: 
       - Critical: Service cannot function without it
       - Non-critical: Service can degrade gracefully
    
    2. **Fast Checks**: Each check should complete in < 5s
    
    3. **Separate Endpoints**:
       - `/health/live` → liveness (restart if fails)
       - `/health/ready` → readiness (route traffic if succeeds)
       - `/health` → full check (monitoring dashboard)
    
    4. **Cache Results**: For high-traffic services, cache health results for 30-60s
    
    5. **Monitor State Changes**: Alert when status changes (healthy → unhealthy)
    
    6. **Test Regularly**: Include health check tests in your test suite
    
    Thread Safety:
    --------------
    This service uses a singleton pattern with lazy initialization.
    Multiple calls to get_health_service() return the same instance.
    Concurrent health checks are safe and run in parallel.
    
    Attributes:
        dependencies (List[DependencyCheck]): Registered dependency checks
        settings (Settings): Application settings for auto-discovery
    
    Methods:
        check_all(timeout=30.0): Comprehensive health check of all dependencies
        check_liveness(): Simple liveness probe (always returns healthy)
        check_readiness(timeout=10.0): Readiness probe (checks critical dependencies)
        add_dependency(dep): Register a custom dependency check
        check_dependency(dep): Check a single dependency
    
    Returns:
        Dict[str, Any]: Health check result with status, message, timestamp, dependencies
    
    Example Output:
    ---------------
    ```json
    {
      "status": "healthy",
      "message": "All dependencies healthy",
      "timestamp": "2024-01-15T10:30:00Z",
      "response_time_ms": 234.56,
      "dependencies": [
        {
          "name": "SQL Database",
          "critical": true,
          "status": "healthy",
          "response_time_ms": 15.23,
          "message": "SQL Database is healthy",
          "details": {
            "server": "prod-db.database.windows.net",
            "database": "docdb"
          }
        }
      ],
      "summary": {
        "total": 10,
        "healthy": 10,
        "degraded": 0,
        "unhealthy": 0,
        "critical_unhealthy": 0,
        "non_critical_unhealthy": 0
      }
    }
    ```
    
    See Also:
        - DependencyCheck: Base class for custom health checks
        - HTTPDependencyCheck: Check HTTP endpoints
        - RedisDependencyCheck: Check Redis cache
        - DatabaseDependencyCheck: Check SQL database
        - AzureServiceDependencyCheck: Check Azure services
    
    References:
        - https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
        - https://microservices.io/patterns/observability/health-check-api.html
    """
    
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

