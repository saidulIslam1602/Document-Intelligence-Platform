"""
Enterprise Configuration Management
Handles all configuration settings for the Document Intelligence Platform
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class AzureConfig:
    """Azure service configuration"""
    subscription_id: str
    resource_group: str
    location: str
    tenant_id: str
    
    # Storage
    storage_account_name: str
    storage_connection_string: str
    storage_account_key: str
    
    # Data Lake Storage
    data_lake_storage_account_name: str
    data_lake_connection_string: str
    data_lake_account_key: str
    
    # AI Services
    form_recognizer_endpoint: str
    form_recognizer_key: str
    openai_endpoint: str
    openai_api_key: str
    openai_deployment: str
    cognitive_search_endpoint: str
    cognitive_search_key: str
    
    # Database
    sql_connection_string: str
    sql_server_name: str
    sql_database_name: str
    
    # Migration Databases
    teradata_host: str = ""
    teradata_user: str = ""
    teradata_password: str = ""
    teradata_database: str = ""
    netezza_host: str = ""
    netezza_user: str = ""
    netezza_password: str = ""
    netezza_database: str = ""
    oracle_host: str = ""
    oracle_user: str = ""
    oracle_password: str = ""
    oracle_database: str = ""
    
    # Event Services
    event_hub_connection_string: str
    service_bus_connection_string: str
    
    # Security
    key_vault_url: str
    client_id: str
    client_secret: str
    
    # Monitoring
    application_insights_connection_string: str
    log_analytics_workspace_id: str

@dataclass
class DocumentProcessingConfig:
    """Document processing configuration"""
    supported_formats: List[str] = field(default_factory=lambda: [
        '.pdf', '.docx', '.doc', '.txt', '.rtf',
        '.jpg', '.jpeg', '.png', '.tiff', '.bmp',
        '.xlsx', '.xls', '.csv', '.pptx', '.ppt'
    ])
    
    max_file_size_mb: int = 50
    max_batch_size: int = 100
    processing_timeout_seconds: int = 300
    
    # AI Processing
    enable_ai_processing: bool = True
    enable_ocr: bool = True
    enable_classification: bool = True
    enable_entity_extraction: bool = True
    enable_sentiment_analysis: bool = True
    
    # Performance
    concurrent_processing_limit: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: int = 5

@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_authentication: bool = True
    enable_authorization: bool = True
    enable_encryption: bool = True
    enable_audit_logging: bool = True
    
    # JWT Settings
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # CORS Settings
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    allowed_headers: List[str] = field(default_factory=lambda: ["*"])

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    enable_application_insights: bool = True
    enable_custom_metrics: bool = True
    enable_distributed_tracing: bool = True
    enable_health_checks: bool = True
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "json"
    enable_structured_logging: bool = True
    
    # Metrics
    metrics_collection_interval: int = 60  # seconds
    enable_business_metrics: bool = True
    enable_performance_metrics: bool = True

@dataclass
class APIConfig:
    """API configuration"""
    api_version: str = "v1"
    base_url: str = ""
    rate_limit_requests_per_minute: int = 1000
    rate_limit_burst: int = 100
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Caching
    enable_response_caching: bool = True
    cache_ttl_seconds: int = 300

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self._azure_config: Optional[AzureConfig] = None
        self._document_config: Optional[DocumentProcessingConfig] = None
        self._security_config: Optional[SecurityConfig] = None
        self._monitoring_config: Optional[MonitoringConfig] = None
        self._api_config: Optional[APIConfig] = None
        
        # Initialize Key Vault client if in production
        if environment == Environment.PRODUCTION:
            self._key_vault_client = SecretClient(
                vault_url=os.getenv("KEY_VAULT_URL", ""),
                credential=DefaultAzureCredential()
            )
        else:
            self._key_vault_client = None
    
    def get_azure_config(self) -> AzureConfig:
        """Get Azure configuration"""
        if self._azure_config is None:
            self._azure_config = self._load_azure_config()
        return self._azure_config
    
    def get_document_config(self) -> DocumentProcessingConfig:
        """Get document processing configuration"""
        if self._document_config is None:
            self._document_config = DocumentProcessingConfig()
        return self._document_config
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        if self._security_config is None:
            self._security_config = self._load_security_config()
        return self._security_config
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        if self._monitoring_config is None:
            self._monitoring_config = MonitoringConfig()
        return self._monitoring_config
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration"""
        if self._api_config is None:
            self._api_config = APIConfig()
        return self._api_config
    
    def _load_azure_config(self) -> AzureConfig:
        """Load Azure configuration from environment or Key Vault"""
        if self.environment == Environment.PRODUCTION and self._key_vault_client:
            return self._load_from_key_vault()
        else:
            return self._load_from_environment()
    
    def _load_from_environment(self) -> AzureConfig:
        """Load configuration from environment variables"""
        return AzureConfig(
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", ""),
            resource_group=os.getenv("AZURE_RESOURCE_GROUP", "document-intelligence-rg"),
            location=os.getenv("AZURE_LOCATION", "East US"),
            tenant_id=os.getenv("AZURE_TENANT_ID", ""),
            
            # Storage
            storage_account_name=os.getenv("STORAGE_ACCOUNT_NAME", ""),
            storage_connection_string=os.getenv("STORAGE_CONNECTION_STRING", ""),
            storage_account_key=os.getenv("STORAGE_ACCOUNT_KEY", ""),
            
            # Data Lake Storage
            data_lake_storage_account_name=os.getenv("DATA_LAKE_STORAGE_ACCOUNT_NAME", ""),
            data_lake_connection_string=os.getenv("DATA_LAKE_CONNECTION_STRING", ""),
            data_lake_account_key=os.getenv("DATA_LAKE_ACCOUNT_KEY", ""),
            
            # AI Services
            form_recognizer_endpoint=os.getenv("FORM_RECOGNIZER_ENDPOINT", ""),
            form_recognizer_key=os.getenv("FORM_RECOGNIZER_KEY", ""),
            openai_endpoint=os.getenv("OPENAI_ENDPOINT", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_deployment=os.getenv("OPENAI_DEPLOYMENT", "gpt-4"),
            cognitive_search_endpoint=os.getenv("COGNITIVE_SEARCH_ENDPOINT", ""),
            cognitive_search_key=os.getenv("COGNITIVE_SEARCH_KEY", ""),
            
            # Databases
            sql_connection_string=os.getenv("SQL_CONNECTION_STRING", ""),
            sql_server_name=os.getenv("SQL_SERVER_NAME", ""),
            sql_database_name=os.getenv("SQL_DATABASE_NAME", "documentintelligence"),
            
            # Migration Databases
            teradata_host=os.getenv("TERADATA_HOST", ""),
            teradata_user=os.getenv("TERADATA_USER", ""),
            teradata_password=os.getenv("TERADATA_PASSWORD", ""),
            teradata_database=os.getenv("TERADATA_DATABASE", ""),
            netezza_host=os.getenv("NETEZZA_HOST", ""),
            netezza_user=os.getenv("NETEZZA_USER", ""),
            netezza_password=os.getenv("NETEZZA_PASSWORD", ""),
            netezza_database=os.getenv("NETEZZA_DATABASE", ""),
            oracle_host=os.getenv("ORACLE_HOST", ""),
            oracle_user=os.getenv("ORACLE_USER", ""),
            oracle_password=os.getenv("ORACLE_PASSWORD", ""),
            oracle_database=os.getenv("ORACLE_DATABASE", ""),
            
            # Event Services
            event_hub_connection_string=os.getenv("EVENT_HUB_CONNECTION_STRING", ""),
            service_bus_connection_string=os.getenv("SERVICE_BUS_CONNECTION_STRING", ""),
            
            # Security
            key_vault_url=os.getenv("KEY_VAULT_URL", ""),
            client_id=os.getenv("CLIENT_ID", ""),
            client_secret=os.getenv("CLIENT_SECRET", ""),
            
            # Monitoring
            application_insights_connection_string=os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING", ""),
            log_analytics_workspace_id=os.getenv("LOG_ANALYTICS_WORKSPACE_ID", "")
        )
    
    def _load_from_key_vault(self) -> AzureConfig:
        """Load configuration from Azure Key Vault"""
        # Implementation for production Key Vault access
        # This would retrieve secrets from Key Vault
        pass
    
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration"""
        return SecurityConfig(
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
            allowed_origins=json.loads(os.getenv("ALLOWED_ORIGINS", '["*"]')),
            allowed_methods=json.loads(os.getenv("ALLOWED_METHODS", '["GET", "POST", "PUT", "DELETE"]')),
            allowed_headers=json.loads(os.getenv("ALLOWED_HEADERS", '["*"]'))
        )
    
    def get_secret(self, secret_name: str) -> str:
        """Get secret from Key Vault or environment"""
        if self.environment == Environment.PRODUCTION and self._key_vault_client:
            try:
                secret = self._key_vault_client.get_secret(secret_name)
                return secret.value
            except Exception as e:
                raise Exception(f"Failed to retrieve secret {secret_name}: {str(e)}")
        else:
            return os.getenv(secret_name, "")

# Global configuration instance
config_manager = ConfigManager(Environment(os.getenv("ENVIRONMENT", "development")))