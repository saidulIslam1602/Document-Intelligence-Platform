"""
Centralized Error Handling Utilities
Eliminates duplicate error handling patterns across microservices
"""

import logging
from typing import Optional, Any, Dict
from fastapi import HTTPException
from functools import wraps

def handle_database_error(operation: str = "database operation"):
    """Decorator for consistent database error handling"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(f"Database error in {operation}: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Database operation failed: {operation}"
                )
        return wrapper
    return decorator

def handle_storage_error(operation: str = "storage operation"):
    """Decorator for consistent storage error handling"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(f"Storage error in {operation}: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Storage operation failed: {operation}"
                )
        return wrapper
    return decorator

def handle_ai_service_error(operation: str = "AI service operation"):
    """Decorator for consistent AI service error handling"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(f"AI service error in {operation}: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"AI service operation failed: {operation}"
                )
        return wrapper
    return decorator

def handle_validation_error(operation: str = "validation"):
    """Decorator for consistent validation error handling"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValueError as e:
                logger = logging.getLogger(func.__module__)
                logger.warning(f"Validation error in {operation}: {str(e)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Validation failed: {str(e)}"
                )
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(f"Unexpected error in {operation}: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Operation failed: {operation}"
                )
        return wrapper
    return decorator

class ErrorHandler:
    """Centralized error handling class"""
    
    @staticmethod
    def log_and_raise(
        logger: logging.Logger,
        error: Exception,
        operation: str,
        status_code: int = 500,
        detail: Optional[str] = None
    ) -> None:
        """Log error and raise HTTPException"""
        logger.error(f"Error in {operation}: {str(error)}")
        raise HTTPException(
            status_code=status_code,
            detail=detail or f"Operation failed: {operation}"
        )
    
    @staticmethod
    def handle_async_operation(
        operation: str,
        status_code: int = 500,
        detail: Optional[str] = None
    ):
        """Decorator for async operation error handling"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger = logging.getLogger(func.__module__)
                    ErrorHandler.log_and_raise(
                        logger, e, operation, status_code, detail
                    )
            return wrapper
        return decorator

# Common error responses
class ErrorResponses:
    """Standard error response templates"""
    
    UNAUTHORIZED = {"detail": "Authentication required"}
    FORBIDDEN = {"detail": "Insufficient permissions"}
    NOT_FOUND = {"detail": "Resource not found"}
    VALIDATION_ERROR = {"detail": "Invalid input data"}
    INTERNAL_ERROR = {"detail": "Internal server error"}
    SERVICE_UNAVAILABLE = {"detail": "Service temporarily unavailable"}
    
    @staticmethod
    def custom_error(message: str, status_code: int = 400) -> Dict[str, Any]:
        """Create custom error response"""
        return {"detail": message, "status_code": status_code}