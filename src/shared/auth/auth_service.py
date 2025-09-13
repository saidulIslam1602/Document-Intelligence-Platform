"""
Centralized Authentication Service
Eliminates duplicate authentication logic across microservices
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