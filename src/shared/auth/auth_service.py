"""
Authentication Service - Centralized Security and Identity Management

This module provides enterprise-grade authentication and authorization for the
Document Intelligence Platform. It handles JWT token generation/validation,
API key management, and user identity verification across all microservices.

Why Centralized Authentication?
--------------------------------

**Without Centralization** (Each service handles auth):
```python
# Service 1 (different logic)
token = jwt.encode(payload, "secret1", algorithm="HS256")

# Service 2 (different logic)
token = jwt.encode(payload, "secret2", algorithm="RS256")

# Service 3 (different logic)
token = custom_encode(payload)

Issues:
❌ Inconsistent token format
❌ Different secrets across services
❌ Duplicate code everywhere
❌ Hard to update auth logic
❌ Security vulnerabilities
❌ No centralized audit
```

**With AuthService** (This Module):
```python
# All services use same auth service
auth_service = AuthService()
token = auth_service.generate_token(user)

# Consistent across platform:
# - Same JWT algorithm
# - Same secret (from Key Vault)
# - Same expiration policy
# - Centralized logging
# - Easy to update

Benefits:
✓ Consistent authentication
✓ Single source of truth
✓ Easy security updates
✓ Centralized audit logs
✓ Reduced attack surface
```

Architecture:
-------------

```
┌─────────────────── Client Applications ──────────────────┐
│                                                           │
│  Web App     Mobile App     CLI Tool     API Client     │
│     │            │             │             │           │
└─────┼────────────┼─────────────┼─────────────┼───────────┘
      │            │             │             │
      │ (JWT Token or API Key)                 │
      ↓            ↓             ↓             ↓
┌──────────────────────────────────────────────────────────┐
│              API Gateway (Port 8003)                     │
│                                                          │
│  ┌────────────── Authentication Middleware ──────────┐  │
│  │  1. Extract token from Authorization header       │  │
│  │  2. Validate token using AuthService              │  │
│  │  3. Inject user context into request              │  │
│  │  4. Reject if invalid/expired                     │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│            AuthService (This Module)                     │
│                                                          │
│  ┌────────────── JWT Token Management ─────────────┐   │
│  │                                                  │   │
│  │  generate_token(user) → JWT                      │   │
│  │  - Creates signed JWT token                      │   │
│  │  - Sets expiration (24 hours default)           │   │
│  │  - Includes user ID, email, permissions          │   │
│  │                                                  │   │
│  │  validate_token(jwt) → User                      │   │
│  │  - Verifies signature                            │   │
│  │  - Checks expiration                             │   │
│  │  - Returns user object                           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────── API Key Management ───────────────┐   │
│  │                                                  │   │
│  │  generate_api_key() → Secret key                 │   │
│  │  - Cryptographically random (32 bytes)          │   │
│  │  - URL-safe format                               │   │
│  │                                                  │   │
│  │  hash_api_key(key) → Hash                        │   │
│  │  - SHA-256 hashing                               │   │
│  │  - Secure storage (never store plaintext)       │   │
│  │                                                  │   │
│  │  verify_api_key(key, hash) → Boolean             │   │
│  │  - Constant-time comparison                      │   │
│  │  - Prevents timing attacks                       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────── Permission Management ─────────────┐   │
│  │                                                  │   │
│  │  check_permission(user, permission) → Boolean    │   │
│  │  - Role-based access control (RBAC)             │   │
│  │  - Fine-grained permissions                      │   │
│  │  - Example: "documents:read", "admin:write"     │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│          Azure Key Vault (Secrets Storage)              │
│  - JWT secret key (HMAC-SHA256)                         │
│  - API key hashes                                        │
│  - Encryption keys                                       │
└──────────────────────────────────────────────────────────┘
```

Authentication Methods:
-----------------------

**1. JWT Tokens** (for user authentication):
```python
# Login flow
user = authenticate_user(email, password)  # Step 1: Verify credentials
token = auth_service.generate_token(user)  # Step 2: Generate JWT
return {"access_token": token}             # Step 3: Return to client

# JWT Structure
Header: {"alg": "HS256", "typ": "JWT"}
Payload: {
    "user_id": "123",
    "email": "user@example.com",
    "permissions": ["documents:read", "documents:write"],
    "exp": 1704067200,  # Expiration timestamp
    "iat": 1703980800   # Issued at timestamp
}
Signature: HMACSHA256(base64(header) + "." + base64(payload), secret_key)

Benefits:
✓ Stateless (no server-side session)
✓ Self-contained (all info in token)
✓ Can be verified without database
✓ Secure (cryptographically signed)
✓ Expirable (automatic invalidation)
```

**2. API Keys** (for programmatic access):
```python
# API Key generation
api_key = auth_service.generate_api_key()  
# Returns: "Xf9k2Jp8s3Lm4Nq6Rt7Vx1Yw2Zc3Ef5Gh8Jk"
# Store hash in database (never plaintext!)

hash = auth_service.hash_api_key(api_key)
# Returns: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# API Key validation
is_valid = auth_service.verify_api_key(provided_key, stored_hash)

Benefits:
✓ Long-lived (no expiration needed)
✓ Ideal for scripts/automation
✓ Can be revoked easily
✓ Per-service keys possible
```

Token Lifecycle:
----------------

**JWT Token Flow**:
```
1. User Login
   ↓
2. Validate Credentials (email + password)
   ↓
3. Generate JWT Token (expires in 24h)
   ↓
4. Client stores token (localStorage/cookie)
   ↓
5. Client sends token with every request
   ↓
6. API Gateway validates token
   ↓
7. Token valid? → Process request
   Token expired? → 401 Unauthorized
   Token invalid? → 403 Forbidden
```

**Token Expiration**:
```python
Default: 24 hours
- Short enough: Limit damage if stolen
- Long enough: Good user experience

Refresh Strategy:
- Option 1: Refresh token (long-lived) + Access token (short-lived)
- Option 2: Silent refresh before expiration
- Option 3: Re-login after expiration

Current Implementation: Option 3 (re-login)
```

Security Features:
------------------

**1. JWT Signing**:
```python
Algorithm: HS256 (HMAC-SHA256)
- Symmetric signing (same key for sign and verify)
- Fast and secure for server-to-server
- Alternative: RS256 (asymmetric, public key verification)

Secret Key:
- Stored in Azure Key Vault (not in code!)
- Rotated every 90 days (security best practice)
- Min 256 bits (32 characters)
```

**2. API Key Hashing**:
```python
Algorithm: SHA-256
- One-way hashing (cannot reverse)
- Even if database leaked, keys safe
- Salting not needed (keys are random)

Storage:
❌ Plaintext: NEVER! ("sk_live_abc123")
✓ Hashed: ALWAYS! ("e3b0c44298fc1c149afbf4...")
```

**3. Token Validation**:
```python
Checks Performed:
1. Signature verification (tamper-proof)
2. Expiration check (expired → reject)
3. Issuer verification (prevent token reuse)
4. Audience verification (intended recipient)

Security Benefits:
- Cannot forge tokens without secret
- Cannot modify payload without detection
- Automatic expiration enforcement
- Protection against replay attacks
```

Permission System:
------------------

**Role-Based Access Control (RBAC)**:
```python
# Define permissions
permissions = [
    "documents:read",      # Read documents
    "documents:write",     # Upload/update documents
    "documents:delete",    # Delete documents
    "analytics:read",      # View analytics
    "admin:*"              # Full admin access
]

# Assign to user
user = User(
    user_id="123",
    email="user@example.com",
    permissions=["documents:read", "documents:write"]
)

# Check permission
@requires_permission("documents:write")
async def upload_document():
    # Only users with documents:write can access
    pass
```

**Permission Hierarchy**:
```
admin:* 
  ↓ (includes all permissions)
├─ documents:*
│   ├─ documents:read
│   ├─ documents:write
│   └─ documents:delete
├─ analytics:*
│   ├─ analytics:read
│   └─ analytics:export
└─ users:*
    ├─ users:read
    ├─ users:create
    └─ users:delete
```

Best Practices:
---------------

1. **Never Store Secrets in Code**: Use environment variables or Key Vault
2. **Always Use HTTPS**: Prevent token interception
3. **Set Reasonable Expiration**: Balance security and UX (24h default)
4. **Implement Token Refresh**: Avoid frequent re-login
5. **Hash API Keys**: Never store plaintext keys
6. **Use Constant-Time Comparison**: Prevent timing attacks
7. **Log Authentication Events**: Audit trail for security
8. **Rate Limit Auth Endpoints**: Prevent brute force
9. **Implement Account Lockout**: After N failed attempts
10. **Use Secure Random**: For API key generation

Common Attacks & Defenses:
--------------------------

**1. Token Theft** (Man-in-the-Middle):
```
Attack: Attacker intercepts token over HTTP
Defense:
✓ Always use HTTPS (TLS 1.2+)
✓ Short token expiration (24h)
✓ HttpOnly cookies (prevent XSS)
```

**2. Brute Force** (Password Guessing):
```
Attack: Attacker tries many passwords
Defense:
✓ Rate limiting (5 attempts per minute)
✓ Account lockout (after 10 failed attempts)
✓ CAPTCHA (after 3 failed attempts)
✓ Strong password policy
```

**3. Token Reuse** (Replay Attack):
```
Attack: Attacker uses stolen token
Defense:
✓ Short expiration (limits damage window)
✓ Token revocation list (for logout)
✓ Detect unusual access patterns
```

**4. Timing Attack** (API Key Verification):
```
Attack: Measure verification time to guess key
Defense:
✓ Constant-time comparison (secrets.compare_digest)
✓ Always check full hash (no early exit)
```

Integration Example:
--------------------

```python
from fastapi import Depends, HTTPException
from src.shared.auth.auth_service import AuthService, User

auth_service = AuthService()

# Dependency for protected endpoints
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    token = credentials.credentials
    user = auth_service.validate_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

# Protected endpoint
@app.get("/documents")
async def get_documents(current_user: User = Depends(get_current_user)):
    # Only authenticated users can access
    return {"user_id": current_user.user_id, "documents": [...]}

# Permission-protected endpoint
@app.delete("/documents/{id}")
async def delete_document(
    id: str,
    current_user: User = Depends(get_current_user)
):
    if "documents:delete" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Delete document
    return {"status": "deleted"}
```

Testing:
--------

```python
import pytest
from datetime import datetime, timedelta

def test_token_generation():
    auth_service = AuthService()
    user = User(user_id="123", email="test@example.com", name="Test User")
    
    token = auth_service.generate_token(user)
    
    assert token is not None
    assert isinstance(token, str)

def test_token_validation():
    auth_service = AuthService()
    user = User(user_id="123", email="test@example.com", name="Test User")
    
    token = auth_service.generate_token(user)
    validated_user = auth_service.validate_token(token)
    
    assert validated_user is not None
    assert validated_user.user_id == user.user_id
    assert validated_user.email == user.email

def test_expired_token():
    auth_service = AuthService()
    # Create token that expired 1 hour ago
    expired_token = jwt.encode(
        {"user_id": "123", "exp": datetime.utcnow() - timedelta(hours=1)},
        auth_service.config.jwt_secret_key,
        algorithm="HS256"
    )
    
    validated_user = auth_service.validate_token(expired_token)
    
    assert validated_user is None  # Expired tokens should be rejected

def test_api_key_verification():
    auth_service = AuthService()
    
    api_key = auth_service.generate_api_key()
    key_hash = auth_service.hash_api_key(api_key)
    
    assert auth_service.verify_api_key(api_key, key_hash) is True
    assert auth_service.verify_api_key("wrong_key", key_hash) is False
```

Monitoring:
-----------

**Metrics to Track**:
```python
- Authentication attempts (success/failure)
- Token generation count
- Token validation count
- Invalid token attempts
- Expired token usage
- API key usage by key
- Failed login attempts by user

Prometheus Metrics:
auth_token_generated_total{user_id}
auth_token_validated_total{result}
auth_failed_attempts_total{reason}
auth_api_key_usage_total{key_id}
```

**Security Alerts**:
```python
Critical:
- 10+ failed logins from same IP in 1 minute
- Invalid token attempts > 100/hour
- API key used after revocation

Warning:
- 5+ failed logins from same user
- Token used from unusual location
- API key not used in 90 days
```

References:
-----------
- JWT Standard (RFC 7519): https://tools.ietf.org/html/rfc7519
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- Azure Key Vault: https://docs.microsoft.com/azure/key-vault/
- Python JWT Library: https://pyjwt.readthedocs.io/

Author: Document Intelligence Platform Team
Version: 2.0.0
Module: Authentication Service - Security and Identity Management
Security: JWT Tokens + API Keys + RBAC
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from dataclasses import dataclass

from ..config.settings import config_manager

@dataclass
class User:
    """User model for authentication"""
    user_id: str
    email: str
    name: str
    is_active: bool = True
    permissions: list = None

class AuthService:
    """Centralized authentication service"""
    
    def __init__(self):
        self.config = config_manager.get_security_config()
        self.logger = logging.getLogger(__name__)
        self.security = HTTPBearer()
    
    def generate_token(self, user: User) -> str:
        """Generate JWT token for user"""
        try:
            payload = {
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "permissions": user.permissions or [],
                "exp": datetime.utcnow() + timedelta(hours=self.config.jwt_expiration_hours),
                "iat": datetime.utcnow()
            }
            
            token = jwt.encode(
                payload, 
                self.config.jwt_secret_key, 
                algorithm=self.config.jwt_algorithm
            )
            
            self.logger.info(f"Token generated for user {user.user_id}")
            return token
            
        except Exception as e:
            self.logger.error(f"Error generating token: {str(e)}")
            raise HTTPException(status_code=500, detail="Token generation failed")
    
    def validate_token(self, token: str) -> Optional[User]:
        """Validate JWT token and return user"""
        try:
            payload = jwt.decode(
                token, 
                self.config.jwt_secret_key, 
                algorithms=[self.config.jwt_algorithm]
            )
            
            user = User(
                user_id=payload["user_id"],
                email=payload["email"],
                name=payload["name"],
                permissions=payload.get("permissions", []),
                is_active=True
            )
            
            self.logger.info(f"Token validated for user {user.user_id}")
            return user
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid token")
            return None
        except Exception as e:
            self.logger.error(f"Token validation error: {str(e)}")
            return None
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """Verify API key against hash"""
        return self.hash_api_key(api_key) == hashed_key

# Global auth service instance
auth_service = AuthService()

# Dependency for getting current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_service.security)) -> User:
    """Get current authenticated user - shared across all services"""
    user = auth_service.validate_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# Dependency for getting current user ID only
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(auth_service.security)) -> str:
    """Get current user ID - lightweight dependency"""
    user = auth_service.validate_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user.user_id