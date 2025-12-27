"""
MCP Server Authentication & Authorization
Implements JWT validation, role-based access control, and audit logging
"""

import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security scheme
security = HTTPBearer()

# Role definitions
class UserRole:
    """User roles for access control"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    VIEWER = "viewer"
    AI_AGENT = "ai_agent"  # Special role for AI agents


class User(BaseModel):
    """User model with role and permissions"""
    user_id: str
    email: Optional[str] = None
    role: str = UserRole.VIEWER
    permissions: List[str] = []
    metadata: Dict[str, Any] = {}


class MCPPermissions:
    """MCP Tool and Resource permissions"""
    
    # Tool permissions
    EXTRACT_INVOICE = "mcp:tool:extract_invoice"
    VALIDATE_INVOICE = "mcp:tool:validate_invoice"
    CLASSIFY_DOCUMENT = "mcp:tool:classify_document"
    CREATE_FINE_TUNING = "mcp:tool:create_fine_tuning"
    GET_METRICS = "mcp:tool:get_metrics"
    PROCESS_M365 = "mcp:tool:process_m365"
    ANALYZE_SENTIMENT = "mcp:tool:analyze_sentiment"
    EXTRACT_ENTITIES = "mcp:tool:extract_entities"
    GENERATE_SUMMARY = "mcp:tool:generate_summary"
    SEARCH_DOCUMENTS = "mcp:tool:search_documents"
    
    # Resource permissions
    READ_DOCUMENT = "mcp:resource:read_document"
    READ_ANALYTICS = "mcp:resource:read_analytics"
    READ_AUTOMATION = "mcp:resource:read_automation"
    READ_INVOICE = "mcp:resource:read_invoice"
    READ_FINE_TUNING = "mcp:resource:read_fine_tuning"
    READ_QUALITY = "mcp:resource:read_quality"
    READ_SEARCH_INDEX = "mcp:resource:read_search_index"
    
    # Admin permissions
    MANAGE_USERS = "mcp:admin:manage_users"
    VIEW_AUDIT_LOGS = "mcp:admin:view_audit_logs"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    UserRole.ADMIN: [
        # All tool permissions
        MCPPermissions.EXTRACT_INVOICE,
        MCPPermissions.VALIDATE_INVOICE,
        MCPPermissions.CLASSIFY_DOCUMENT,
        MCPPermissions.CREATE_FINE_TUNING,
        MCPPermissions.GET_METRICS,
        MCPPermissions.PROCESS_M365,
        MCPPermissions.ANALYZE_SENTIMENT,
        MCPPermissions.EXTRACT_ENTITIES,
        MCPPermissions.GENERATE_SUMMARY,
        MCPPermissions.SEARCH_DOCUMENTS,
        # All resource permissions
        MCPPermissions.READ_DOCUMENT,
        MCPPermissions.READ_ANALYTICS,
        MCPPermissions.READ_AUTOMATION,
        MCPPermissions.READ_INVOICE,
        MCPPermissions.READ_FINE_TUNING,
        MCPPermissions.READ_QUALITY,
        MCPPermissions.READ_SEARCH_INDEX,
        # Admin permissions
        MCPPermissions.MANAGE_USERS,
        MCPPermissions.VIEW_AUDIT_LOGS,
    ],
    UserRole.DEVELOPER: [
        # Most tool permissions except admin operations
        MCPPermissions.EXTRACT_INVOICE,
        MCPPermissions.VALIDATE_INVOICE,
        MCPPermissions.CLASSIFY_DOCUMENT,
        MCPPermissions.CREATE_FINE_TUNING,
        MCPPermissions.GET_METRICS,
        MCPPermissions.PROCESS_M365,
        MCPPermissions.ANALYZE_SENTIMENT,
        MCPPermissions.EXTRACT_ENTITIES,
        MCPPermissions.GENERATE_SUMMARY,
        MCPPermissions.SEARCH_DOCUMENTS,
        # All resource permissions
        MCPPermissions.READ_DOCUMENT,
        MCPPermissions.READ_ANALYTICS,
        MCPPermissions.READ_AUTOMATION,
        MCPPermissions.READ_INVOICE,
        MCPPermissions.READ_FINE_TUNING,
        MCPPermissions.READ_QUALITY,
        MCPPermissions.READ_SEARCH_INDEX,
    ],
    UserRole.ANALYST: [
        # Read-only tools and analytics
        MCPPermissions.GET_METRICS,
        MCPPermissions.SEARCH_DOCUMENTS,
        MCPPermissions.ANALYZE_SENTIMENT,
        MCPPermissions.EXTRACT_ENTITIES,
        MCPPermissions.GENERATE_SUMMARY,
        # Read resources only
        MCPPermissions.READ_DOCUMENT,
        MCPPermissions.READ_ANALYTICS,
        MCPPermissions.READ_AUTOMATION,
        MCPPermissions.READ_INVOICE,
        MCPPermissions.READ_QUALITY,
        MCPPermissions.READ_SEARCH_INDEX,
    ],
    UserRole.VIEWER: [
        # Very limited access
        MCPPermissions.GET_METRICS,
        MCPPermissions.READ_ANALYTICS,
        MCPPermissions.READ_AUTOMATION,
    ],
    UserRole.AI_AGENT: [
        # AI agents get processing permissions but not admin
        MCPPermissions.EXTRACT_INVOICE,
        MCPPermissions.VALIDATE_INVOICE,
        MCPPermissions.CLASSIFY_DOCUMENT,
        MCPPermissions.GET_METRICS,
        MCPPermissions.ANALYZE_SENTIMENT,
        MCPPermissions.EXTRACT_ENTITIES,
        MCPPermissions.GENERATE_SUMMARY,
        MCPPermissions.SEARCH_DOCUMENTS,
        # Read resources
        MCPPermissions.READ_DOCUMENT,
        MCPPermissions.READ_ANALYTICS,
        MCPPermissions.READ_AUTOMATION,
        MCPPermissions.READ_INVOICE,
        MCPPermissions.READ_QUALITY,
        MCPPermissions.READ_SEARCH_INDEX,
    ],
}

# Tool name to permission mapping
TOOL_PERMISSIONS: Dict[str, str] = {
    "extract_invoice_data": MCPPermissions.EXTRACT_INVOICE,
    "validate_invoice": MCPPermissions.VALIDATE_INVOICE,
    "classify_document": MCPPermissions.CLASSIFY_DOCUMENT,
    "create_fine_tuning_job": MCPPermissions.CREATE_FINE_TUNING,
    "get_automation_metrics": MCPPermissions.GET_METRICS,
    "process_m365_document": MCPPermissions.PROCESS_M365,
    "analyze_document_sentiment": MCPPermissions.ANALYZE_SENTIMENT,
    "extract_document_entities": MCPPermissions.EXTRACT_ENTITIES,
    "generate_document_summary": MCPPermissions.GENERATE_SUMMARY,
    "search_documents": MCPPermissions.SEARCH_DOCUMENTS,
}

# Resource type to permission mapping
RESOURCE_PERMISSIONS: Dict[str, str] = {
    "document": MCPPermissions.READ_DOCUMENT,
    "analytics": MCPPermissions.READ_ANALYTICS,
    "automation": MCPPermissions.READ_AUTOMATION,
    "invoice": MCPPermissions.READ_INVOICE,
    "fine-tuning": MCPPermissions.READ_FINE_TUNING,
    "quality": MCPPermissions.READ_QUALITY,
    "search": MCPPermissions.READ_SEARCH_INDEX,
}


class JWTValidator:
    """JWT token validation"""
    
    @staticmethod
    def create_token(user_id: str, role: str, metadata: Dict[str, Any] = None) -> str:
        """Create a JWT token for a user"""
        payload = {
            "user_id": user_id,
            "role": role,
            "metadata": metadata or {},
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """Validate JWT token and return payload"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


class AccessController:
    """Role-based access control"""
    
    @staticmethod
    def get_role_permissions(role: str) -> List[str]:
        """Get permissions for a role"""
        return ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """Check if user has a specific permission"""
        # Check explicit permissions
        if permission in user.permissions:
            return True
        
        # Check role-based permissions
        role_permissions = AccessController.get_role_permissions(user.role)
        return permission in role_permissions
    
    @staticmethod
    def check_tool_access(user: User, tool_name: str) -> None:
        """Check if user can execute a tool"""
        required_permission = TOOL_PERMISSIONS.get(tool_name)
        
        if not required_permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found"
            )
        
        if not AccessController.has_permission(user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have permission to execute tool '{tool_name}'"
            )
    
    @staticmethod
    def check_resource_access(user: User, resource_type: str) -> None:
        """Check if user can read a resource"""
        required_permission = RESOURCE_PERMISSIONS.get(resource_type)
        
        if not required_permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource type '{resource_type}' not found"
            )
        
        if not AccessController.has_permission(user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have permission to read resource type '{resource_type}'"
            )


class AuditLogger:
    """Audit logging for MCP operations"""
    
    @staticmethod
    def log_tool_execution(
        user_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        execution_time: float = 0.0
    ) -> None:
        """Log MCP tool execution"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "mcp_tool_execution",
            "user_id": user_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "success": success,
            "error": error,
            "execution_time": execution_time,
        }
        
        # Log to application logger
        if success:
            logger.info(f"MCP Tool Executed: {tool_name} by {user_id} (success={success}, time={execution_time:.2f}s)")
        else:
            logger.warning(f"MCP Tool Failed: {tool_name} by {user_id} - {error}")
        
        # In production, also send to audit storage (database, Azure Monitor, etc.)
        # await audit_storage.store(log_entry)
    
    @staticmethod
    def log_resource_access(
        user_id: str,
        resource_uri: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log MCP resource access"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "mcp_resource_access",
            "user_id": user_id,
            "resource_uri": resource_uri,
            "success": success,
            "error": error,
        }
        
        # Log to application logger
        if success:
            logger.info(f"MCP Resource Accessed: {resource_uri} by {user_id}")
        else:
            logger.warning(f"MCP Resource Access Failed: {resource_uri} by {user_id} - {error}")
        
        # In production, also send to audit storage
        # await audit_storage.store(log_entry)
    
    @staticmethod
    def log_authentication(
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log authentication attempts"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "mcp_authentication",
            "user_id": user_id,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        
        if success:
            logger.info(f"MCP Authentication Success: {user_id} from {ip_address}")
        else:
            logger.warning(f"MCP Authentication Failed: {user_id} from {ip_address}")
        
        # In production, send to audit storage and potentially trigger alerts for failed attempts
        # await audit_storage.store(log_entry)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    
    Usage:
        @app.post("/endpoint")
        async def endpoint(user: User = Depends(get_current_user)):
            # user is authenticated and validated
            pass
    """
    try:
        # Extract token from Bearer header
        token = credentials.credentials
        
        # Validate JWT token
        payload = JWTValidator.validate_token(token)
        
        # Extract user information
        user_id = payload.get("user_id")
        role = payload.get("role", UserRole.VIEWER)
        metadata = payload.get("metadata", {})
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        # Create User object with permissions
        user = User(
            user_id=user_id,
            role=role,
            permissions=AccessController.get_role_permissions(role),
            metadata=metadata
        )
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str):
    """
    Decorator to require specific permission
    
    Usage:
        @app.post("/endpoint")
        @require_permission(MCPPermissions.EXTRACT_INVOICE)
        async def endpoint(user: User = Depends(get_current_user)):
            pass
    """
    def decorator(func):
        async def wrapper(*args, user: User = None, **kwargs):
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not AccessController.has_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
            
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator


# Utility function to generate tokens (for testing/development)
def generate_test_tokens() -> Dict[str, str]:
    """Generate test tokens for different roles"""
    tokens = {}
    
    for role in [UserRole.ADMIN, UserRole.DEVELOPER, UserRole.ANALYST, UserRole.VIEWER, UserRole.AI_AGENT]:
        token = JWTValidator.create_token(
            user_id=f"test_{role}",
            role=role,
            metadata={"test": True}
        )
        tokens[role] = token
    
    return tokens


if __name__ == "__main__":
    # Generate test tokens for development
    print("=== MCP Server Test Tokens ===\n")
    tokens = generate_test_tokens()
    
    for role, token in tokens.items():
        print(f"{role.upper()}:")
        print(f"Token: {token}\n")
        print(f"Permissions: {len(ROLE_PERMISSIONS.get(role, []))} permissions")
        print(f"  - {', '.join(ROLE_PERMISSIONS.get(role, [])[:3])}...\n")

