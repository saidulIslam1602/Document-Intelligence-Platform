"""
Enhanced Configuration Management System
Centralized, type-safe configuration for all microservices
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 100
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    
    class Config:
        env_prefix = "REDIS_"
        env_file = ".env"
        case_sensitive = False


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    connection_string: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo_sql: bool = False
    
    class Config:
        env_prefix = "DB_"
        env_file = ".env"


class FormRecognizerSettings(BaseSettings):
    """Form Recognizer configuration"""
    endpoint: str
    key: str
    max_retries: int = 3
    timeout: int = 30
    rate_limit_per_second: float = 15.0
    rate_limit_burst: float = 30.0
    
    class Config:
        env_prefix = "FORM_RECOGNIZER_"
        env_file = ".env"


class AutomationSettings(BaseSettings):
    """Automation scoring configuration"""
    threshold: float = 0.85
    confidence_threshold: float = 0.90
    completeness_threshold: float = 0.95
    goal: float = 0.90
    validation_threshold: float = 0.85
    manual_intervention_threshold: float = 0.70
    
    class Config:
        env_prefix = "AUTOMATION_"
        env_file = ".env"


class PerformanceSettings(BaseSettings):
    """Performance tuning configuration"""
    # HTTP Client Settings
    http_max_connections: int = 200
    http_max_keepalive: int = 100
    http_timeout_connect: int = 5
    http_timeout_read: int = 30
    http_timeout_write: int = 10
    http_timeout_pool: int = 5
    http2_enabled: bool = True
    
    # Database Settings
    async_sql_pool_size: int = 10
    async_sql_max_overflow: int = 20
    
    # Batch Processing Settings
    batch_size: int = 100
    batch_flush_interval: int = 30
    
    # Cache Settings
    cache_ttl: int = 300
    cache_max_size: int = 10000
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_second: float = 100.0
    
    class Config:
        env_prefix = "PERF_"
        env_file = ".env"


class CircuitBreakerSettings(BaseSettings):
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    timeout: float = 60.0
    half_open_timeout: float = 10.0
    enabled: bool = True
    
    class Config:
        env_prefix = "CIRCUIT_BREAKER_"
        env_file = ".env"


class RetrySettings(BaseSettings):
    """Retry configuration"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    class Config:
        env_prefix = "RETRY_"
        env_file = ".env"


class ObservabilitySettings(BaseSettings):
    """Observability configuration"""
    tracing_enabled: bool = True
    metrics_enabled: bool = True
    jaeger_host: str = "jaeger"
    jaeger_port: int = 6831
    prometheus_port: int = 9090
    
    class Config:
        env_prefix = "OBSERVABILITY_"
        env_file = ".env"


class ServiceSettings(BaseSettings):
    """Service-specific configuration"""
    name: str
    port: int
    host: str = "0.0.0.0"
    workers: int = 4
    reload: bool = False
    
    class Config:
        env_prefix = "SERVICE_"
        env_file = ".env"


class AppSettings(BaseSettings):
    """Main application settings"""
    # Environment
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Service Configuration
    service: ServiceSettings = ServiceSettings(
        name=os.getenv("SERVICE_NAME", "document-intelligence"),
        port=int(os.getenv("SERVICE_PORT", "8000"))
    )
    
    # Component Settings
    redis: RedisSettings = RedisSettings()
    database: DatabaseSettings = DatabaseSettings(
        connection_string=os.getenv("SQL_CONNECTION_STRING", "")
    )
    form_recognizer: FormRecognizerSettings = FormRecognizerSettings(
        endpoint=os.getenv("FORM_RECOGNIZER_ENDPOINT", ""),
        key=os.getenv("FORM_RECOGNIZER_KEY", "")
    )
    automation: AutomationSettings = AutomationSettings()
    performance: PerformanceSettings = PerformanceSettings()
    circuit_breaker: CircuitBreakerSettings = CircuitBreakerSettings()
    retry: RetrySettings = RetrySettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"


@lru_cache()
def get_settings() -> AppSettings:
    """Get cached settings instance"""
    return AppSettings()


# Convenience function for quick access
def get_config() -> AppSettings:
    """Get application configuration"""
    return get_settings()


# Export settings instance
settings = get_settings()

