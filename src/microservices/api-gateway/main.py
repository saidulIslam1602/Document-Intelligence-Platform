"""
API Gateway Microservice
Centralized API gateway with authentication, rate limiting, and routing
"""

import asyncio
import logging
import os
import time
import hashlib
import jwt
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import httpx
from starlette.middleware.base import BaseHTTPMiddleware

from ...shared.config.settings import config_manager
from ...shared.health import get_health_service
from ...shared.resilience.circuit_breaker import CircuitBreakerRegistry
from ...shared.rate_limiting import RateLimiterRegistry

# Initialize FastAPI app
app = FastAPI(
    title="API Gateway",
    description="Centralized API gateway for Document Intelligence Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Security
security = HTTPBearer()

# Global variables
config = config_manager.get_azure_config()
logger = logging.getLogger(__name__)

# Redis configuration from environment variables
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')  # Default to 'redis' for Docker, not 'localhost'
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# Redis client for rate limiting and caching
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    db=REDIS_DB, 
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

# Key Vault client for secrets
key_vault_client = SecretClient(
    vault_url=config.key_vault_url,
    credential=DefaultAzureCredential()
)

# Service endpoints
SERVICE_ENDPOINTS = {
    "document-ingestion": "http://document-ingestion:8000",
    "ai-processing": "http://ai-processing:8001",
    "analytics": "http://analytics:8002",
    "user-management": "http://user-management:8003",
    "ai-chat": "http://ai-chat:8004",
    "performance-dashboard": "http://performance-dashboard:8005",
    "data-quality": "http://data-quality:8006",
    "batch-processor": "http://batch-processor:8007",
    "data-catalog": "http://data-catalog:8008",
    "migration-service": "http://migration-service:8009",
    "fabric-integration": "http://fabric-integration:8010",
    "demo-service": "http://demo-service:8011",
    "mcp-server": "http://mcp-server:8012"
}

# Rate limiting configuration
RATE_LIMITS = {
    "default": {"requests": 1000, "window": 3600},  # 1000 requests per hour
    "document-upload": {"requests": 100, "window": 3600},  # 100 uploads per hour
    "ai-processing": {"requests": 500, "window": 3600},  # 500 AI requests per hour
    "analytics": {"requests": 2000, "window": 3600},  # 2000 analytics requests per hour
}

# Pydantic models
class User(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None

class APIKey(BaseModel):
    key_id: str
    user_id: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True

class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime
    request_id: str

# Middleware for request processing
class RequestProcessingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Add request ID
        request_id = hashlib.md5(f"{request.url}{time.time()}".encode()).hexdigest()[:8]
        request.state.request_id = request_id
        
        # Add timestamp
        request.state.start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add processing time
        processing_time = time.time() - request.state.start_time
        response.headers["X-Processing-Time"] = str(processing_time)
        response.headers["X-Request-ID"] = request_id
        
        return response

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        
        # Get rate limit key
        rate_limit_key = f"rate_limit:{client_ip}:{request.url.path}"
        
        # Check rate limit
        if not await self.check_rate_limit(rate_limit_key, request.url.path):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        return response
    
    async def check_rate_limit(self, key: str, path: str) -> bool:
        """Check if request is within rate limit"""
        try:
            # Get rate limit configuration
            rate_limit = RATE_LIMITS.get("default")
            for pattern, limit in RATE_LIMITS.items():
                if pattern in path:
                    rate_limit = limit
                    break
            
            # Check current count
            current_count = redis_client.get(key)
            if current_count is None:
                # First request in window
                redis_client.setex(key, rate_limit["window"], 1)
                return True
            
            current_count = int(current_count)
            if current_count >= rate_limit["requests"]:
                return False
            
            # Increment counter
            redis_client.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True  # Allow request on error

# Authentication middleware
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for health checks and public endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"error": "Authorization header required"}
            )
        
        try:
            # Extract token
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid authorization scheme"}
                )
            
            # Validate token
            user = await self.validate_token(token)
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid or expired token"}
                )
            
            # Add user to request state
            request.state.user = user
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication failed"}
            )
        
        return await call_next(request)
    
    async def validate_token(self, token: str) -> Optional[User]:
        """Validate JWT token and return user information"""
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                config.jwt_secret_key,
                algorithms=["HS256"],
                options={"verify_exp": True}
            )
            
            # Extract user information
            user_id = payload.get("user_id")
            email = payload.get("email")
            role = payload.get("role", "user")
            permissions = payload.get("permissions", [])
            
            if not user_id or not email:
                return None
            
            return User(
                user_id=user_id,
                email=email,
                role=role,
                permissions=permissions,
                created_at=datetime.fromisoformat(payload.get("created_at", datetime.utcnow().isoformat())),
                last_login=datetime.fromisoformat(payload.get("last_login", datetime.utcnow().isoformat()))
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None

# Add middleware
app.add_middleware(RequestProcessingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint
    Checks all dependencies and downstream services
    """
    health_service = get_health_service()
    health_result = await health_service.check_all()
    
    # Add service metadata
    health_result["service"] = "api-gateway"
    health_result["version"] = "1.0.0"
    
    # Set HTTP status based on health
    status_code = 200
    if health_result["status"] == "unhealthy":
        status_code = 503
    elif health_result["status"] == "degraded":
        status_code = 200  # Still accepting traffic
    
    return JSONResponse(content=health_result, status_code=status_code)


@app.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe
    Returns 200 if service is alive (running)
    """
    health_service = get_health_service()
    result = await health_service.check_liveness()
    return JSONResponse(content=result, status_code=200)


@app.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe
    Returns 200 if service is ready to accept traffic
    """
    health_service = get_health_service()
    result = await health_service.check_readiness()
    
    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/circuit-breakers")
async def get_circuit_breakers():
    """
    Get status of all circuit breakers
    Useful for monitoring and debugging
    """
    states = CircuitBreakerRegistry.get_all_states()
    
    # Calculate overall health
    total = len(states)
    open_count = sum(1 for s in states.values() if s["state"] == "open")
    half_open_count = sum(1 for s in states.values() if s["state"] == "half_open")
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_breakers": total,
            "open": open_count,
            "half_open": half_open_count,
            "closed": total - open_count - half_open_count,
            "health": "degraded" if open_count > 0 else "healthy"
        },
        "breakers": states
    }


@app.post("/circuit-breakers/{breaker_name}/reset")
async def reset_circuit_breaker(breaker_name: str):
    """
    Manually reset a circuit breaker to CLOSED state
    Useful for recovery after fixing issues
    """
    breakers = CircuitBreakerRegistry.get_all()
    
    if breaker_name not in breakers:
        raise HTTPException(status_code=404, detail=f"Circuit breaker '{breaker_name}' not found")
    
    breaker = breakers[breaker_name]
    breaker.reset()
    
    return {
        "message": f"Circuit breaker '{breaker_name}' reset to CLOSED",
        "state": breaker.get_state()
    }


@app.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers():
    """
    Reset all circuit breakers to CLOSED state
    Use with caution - only after fixing underlying issues
    """
    CircuitBreakerRegistry.reset_all()
    
    return {
        "message": "All circuit breakers reset to CLOSED",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/rate-limiters")
async def get_rate_limiters():
    """
    Get status of all rate limiters
    Shows current token count, request stats, and wait times
    """
    stats = RateLimiterRegistry.get_all_stats()
    
    # Calculate overall statistics
    total_requests = sum(s["total_requests"] for s in stats.values())
    total_waited = sum(s["total_waited"] for s in stats.values())
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_limiters": len(stats),
            "total_requests": total_requests,
            "total_waited": total_waited,
            "overall_wait_rate": (total_waited / total_requests * 100) 
                if total_requests > 0 else 0.0
        },
        "limiters": stats
    }


@app.post("/rate-limiters/{limiter_name}/reset")
async def reset_rate_limiter(limiter_name: str):
    """
    Manually reset a rate limiter to initial state
    Useful for clearing statistics or resetting after configuration changes
    """
    limiters = RateLimiterRegistry.get_all()
    
    if limiter_name not in limiters:
        raise HTTPException(status_code=404, detail=f"Rate limiter '{limiter_name}' not found")
    
    limiter = limiters[limiter_name]
    limiter.reset()
    
    return {
        "message": f"Rate limiter '{limiter_name}' reset to initial state",
        "stats": limiter.get_stats()
    }


@app.post("/rate-limiters/reset-all")
async def reset_all_rate_limiters():
    """
    Reset all rate limiters to initial state
    Use to clear all statistics or after configuration changes
    """
    RateLimiterRegistry.reset_all()
    
    return {
        "message": "All rate limiters reset to initial state",
        "timestamp": datetime.utcnow().isoformat()
    }

# Service routing endpoints
@app.api_route("/documents/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_document_requests(request: Request, path: str):
    """Route requests to document ingestion service"""
    return await route_request(request, "document-ingestion", f"/documents/{path}")

@app.api_route("/process/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_processing_requests(request: Request, path: str):
    """Route requests to AI processing service"""
    return await route_request(request, "ai-processing", f"/process/{path}")

@app.api_route("/analytics/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_analytics_requests(request: Request, path: str):
    """Route requests to analytics service"""
    return await route_request(request, "analytics", f"/analytics/{path}")

@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_user_requests(request: Request, path: str):
    """Route requests to user management service"""
    return await route_request(request, "user-management", f"/users/{path}")

@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_mcp_requests(request: Request, path: str):
    """Route requests to MCP server"""
    return await route_request(request, "mcp-server", f"/mcp/{path}")

@app.api_route("/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_chat_requests(request: Request, path: str):
    """Route requests to AI chat service"""
    return await route_request(request, "ai-chat", f"/chat/{path}")

@app.api_route("/quality/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_quality_requests(request: Request, path: str):
    """Route requests to data quality service"""
    return await route_request(request, "data-quality", f"/quality/{path}")

@app.api_route("/llmops/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_llmops_requests(request: Request, path: str):
    """Route requests to AI processing service for LLMOps"""
    return await route_request(request, "ai-processing", f"/llmops/{path}")

# Authentication endpoints
@app.post("/auth/login")
async def login(email: str, password: str):
    """User login endpoint"""
    try:
        # Validate credentials (in production, this would check against database)
        user = await validate_credentials(email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate JWT token
        token = generate_jwt_token(user)
        
        # Update last login
        await update_last_login(user.user_id)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": user.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/refresh")
async def refresh_token(current_token: str = Depends(security)):
    """Refresh JWT token"""
    try:
        # Validate current token
        user = await validate_token(current_token.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Generate new token
        new_token = generate_jwt_token(user)
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/logout")
async def logout(current_token: str = Depends(security)):
    """User logout endpoint"""
    try:
        # Add token to blacklist (in production, this would be stored in Redis)
        token_hash = hashlib.sha256(current_token.credentials.encode()).hexdigest()
        redis_client.setex(f"blacklist:{token_hash}", 3600, "true")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API key management endpoints
@app.post("/api-keys")
async def create_api_key(
    name: str,
    permissions: List[str],
    expires_days: Optional[int] = None,
    user: User = Depends(get_current_user)
):
    """Create a new API key"""
    try:
        # Generate API key
        api_key = generate_api_key()
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        # Set expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Store API key
        api_key_record = APIKey(
            key_id=key_id,
            user_id=user.user_id,
            name=name,
            permissions=permissions,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            is_active=True
        )
        
        await store_api_key(api_key_record, api_key)
        
        return {
            "key_id": key_id,
            "api_key": api_key,
            "name": name,
            "permissions": permissions,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": api_key_record.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api-keys")
async def list_api_keys(user: User = Depends(get_current_user)):
    """List user's API keys"""
    try:
        api_keys = await get_user_api_keys(user.user_id)
        return {"api_keys": [key.dict() for key in api_keys]}
        
    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user: User = Depends(get_current_user)):
    """Revoke an API key"""
    try:
        await revoke_api_key_by_id(key_id, user.user_id)
        return {"message": "API key revoked successfully"}
        
    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Rate limit information endpoint
@app.get("/rate-limit")
async def get_rate_limit_info(request: Request):
    """Get current rate limit information"""
    try:
        client_ip = request.client.host
        rate_limit_key = f"rate_limit:{client_ip}:{request.url.path}"
        
        # Get current count
        current_count = redis_client.get(rate_limit_key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)
        
        # Get rate limit configuration
        rate_limit = RATE_LIMITS.get("default")
        for pattern, limit in RATE_LIMITS.items():
            if pattern in request.url.path:
                rate_limit = limit
                break
        
        # Calculate reset time
        ttl = redis_client.ttl(rate_limit_key)
        reset_time = int(time.time()) + ttl if ttl > 0 else int(time.time()) + rate_limit["window"]
        
        return RateLimitInfo(
            limit=rate_limit["requests"],
            remaining=max(0, rate_limit["requests"] - current_count),
            reset_time=reset_time,
            retry_after=60 if current_count >= rate_limit["requests"] else None
        )
        
    except Exception as e:
        logger.error(f"Error getting rate limit info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Helper functions
async def route_request(request: Request, service_name: str, path: str) -> Response:
    """Route request to appropriate microservice"""
    try:
        service_url = SERVICE_ENDPOINTS.get(service_name)
        if not service_url:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Prepare request data
        request_data = {
            "method": request.method,
            "url": f"{service_url}{path}",
            "headers": dict(request.headers),
            "params": dict(request.query_params)
        }
        
        # Add request body for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            request_data["content"] = body
            request_data["headers"]["content-type"] = request.headers.get("content-type", "application/json")
        
        # Make request to microservice
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(**request_data)
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable")
    except Exception as e:
        logger.error(f"Error routing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def check_service_health(service_name: str) -> Dict[str, Any]:
    """Check health of a microservice"""
    try:
        service_url = SERVICE_ENDPOINTS.get(service_name)
        if not service_url:
            return {"status": "unknown", "error": "Service not configured"}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            
            if response.status_code == 200:
                return {"status": "healthy", "response_time": response.elapsed.total_seconds()}
            else:
                return {"status": "unhealthy", "status_code": response.status_code}
                
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def validate_credentials(email: str, password: str) -> Optional[User]:
    """Validate user credentials"""
    try:
        # In production, this would validate against a database
        # Validate credentials (simplified for development)
        if email and password:
            return User(
                user_id=f"user_{hashlib.md5(email.encode()).hexdigest()[:8]}",
                email=email,
                role="user",
                permissions=["read", "write"],
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
        return None
        
    except Exception as e:
        logger.error(f"Error validating credentials: {str(e)}")
        return None

def generate_jwt_token(user: User) -> str:
    """Generate JWT token for user"""
    payload = {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions,
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, config.jwt_secret_key, algorithm="HS256")

async def validate_token(token: str) -> Optional[User]:
    """Validate JWT token"""
    try:
        # Check if token is blacklisted
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if redis_client.get(f"blacklist:{token_hash}"):
            return None
        
        # Decode token
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=["HS256"])
        
        return User(
            user_id=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            permissions=payload["permissions"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            last_login=datetime.fromisoformat(payload["last_login"]) if payload.get("last_login") else None
        )
        
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        return None

async def update_last_login(user_id: str):
    """Update user's last login timestamp"""
    try:
        # In production, this would update the database
        logger.info(f"Updated last login for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating last login: {str(e)}")

def generate_api_key() -> str:
    """Generate a secure API key"""
    import secrets
    return secrets.token_urlsafe(32)

async def store_api_key(api_key_record: APIKey, api_key: str):
    """Store API key in secure storage"""
    try:
        # In production, this would store in encrypted format
        key_data = {
            "key_id": api_key_record.key_id,
            "user_id": api_key_record.user_id,
            "api_key_hash": hashlib.sha256(api_key.encode()).hexdigest(),
            "name": api_key_record.name,
            "permissions": api_key_record.permissions,
            "created_at": api_key_record.created_at.isoformat(),
            "expires_at": api_key_record.expires_at.isoformat() if api_key_record.expires_at else None,
            "is_active": api_key_record.is_active
        }
        
        # Store in Redis (in production, use a proper database)
        redis_client.setex(
            f"api_key:{api_key_record.key_id}",
            86400 * 365,  # 1 year
            json.dumps(key_data)
        )
        
    except Exception as e:
        logger.error(f"Error storing API key: {str(e)}")
        raise

async def get_user_api_keys(user_id: str) -> List[APIKey]:
    """Get all API keys for a user"""
    try:
        # In production, this would query the database
        # Return empty list (no active sessions in development)
        return []
        
    except Exception as e:
        logger.error(f"Error getting user API keys: {str(e)}")
        return []

async def revoke_api_key_by_id(key_id: str, user_id: str):
    """Revoke an API key by ID"""
    try:
        # In production, this would update the database
        redis_client.delete(f"api_key:{key_id}")
        logger.info(f"API key {key_id} revoked for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}")
        raise

# Dependency injection
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    user = await validate_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("API Gateway Service started")
    
    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("API Gateway Service shutting down")
    redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)