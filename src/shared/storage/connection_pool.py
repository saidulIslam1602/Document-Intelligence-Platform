"""
Connection Pool Manager
Optimizes database and Redis connections for better performance
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import pyodbc
import redis.asyncio as redis

# Azure imports (optional)
try:
    from azure.storage.blob import BlobServiceClient
    from azure.storage.filedatalake import DataLakeServiceClient
    from azure.eventhub import EventHubProducerClient
    from azure.servicebus import ServiceBusClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    BlobServiceClient = None
    DataLakeServiceClient = None
    EventHubProducerClient = None
    ServiceBusClient = None

from ..config.settings import config_manager

class ConnectionPoolManager:
    """Manages connection pools for all services"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        
        # Connection pools
        self._sql_pool = None
        self._redis_pool = None
        self._blob_client = None
        self._data_lake_client = None
        self._event_hub_producer = None
        self._service_bus_client = None
        
        # Pool settings
        self.sql_pool_size = 10
        self.redis_pool_size = 20
        self.max_overflow = 5
        
    async def initialize_pools(self):
        """Initialize all connection pools"""
        try:
            # Initialize SQL connection pool
            await self._init_sql_pool()
            
            # Initialize Redis connection pool
            await self._init_redis_pool()
            
            # Initialize Azure clients
            self._init_azure_clients()
            
            self.logger.info("All connection pools initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pools: {str(e)}")
            raise
    
    async def _init_sql_pool(self):
        """Initialize SQL connection pool"""
        try:
            # Create connection pool using pyodbc
            connection_string = self.config.sql_connection_string
            self._sql_pool = []
            
            # Pre-create connections
            for _ in range(self.sql_pool_size):
                conn = pyodbc.connect(connection_string)
                self._sql_pool.append(conn)
            
            self.logger.info(f"SQL connection pool initialized with {self.sql_pool_size} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SQL pool: {str(e)}")
            raise
    
    async def _init_redis_pool(self):
        """Initialize Redis connection pool"""
        try:
            # Get Redis configuration from environment variables
            redis_host = os.getenv('REDIS_HOST', 'redis')  # Default to 'redis' for Docker
            redis_port = os.getenv('REDIS_PORT', '6379')
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_db = os.getenv('REDIS_DB', '0')
            
            # Build Redis URL
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            
            self._redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=self.redis_pool_size,
                retry_on_timeout=True
            )
            
            # Test connection
            redis_client = redis.Redis(connection_pool=self._redis_pool)
            await redis_client.ping()
            
            self.logger.info(f"Redis connection pool initialized with {self.redis_pool_size} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis pool: {str(e)}")
            raise
    
    def _init_azure_clients(self):
        """Initialize Azure service clients"""
        try:
            # Blob Storage client
            self._blob_client = BlobServiceClient.from_connection_string(
                self.config.storage_connection_string
            )
            
            # Data Lake client
            self._data_lake_client = DataLakeServiceClient.from_connection_string(
                self.config.data_lake_connection_string
            )
            
            # Event Hub producer
            self._event_hub_producer = EventHubProducerClient.from_connection_string(
                self.config.event_hub_connection_string,
                eventhub_name="document-processing"
            )
            
            # Service Bus client
            self._service_bus_client = ServiceBusClient.from_connection_string(
                self.config.service_bus_connection_string
            )
            
            self.logger.info("Azure service clients initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure clients: {str(e)}")
            raise
    
    @asynccontextmanager
    async def get_sql_connection(self):
        """Get SQL connection from pool"""
        if not self._sql_pool:
            await self._init_sql_pool()
        
        conn = None
        try:
            # Get connection from pool
            if self._sql_pool:
                conn = self._sql_pool.pop()
            else:
                # Create new connection if pool is empty
                conn = pyodbc.connect(self.config.sql_connection_string)
            
            yield conn
            
        except Exception as e:
            self.logger.error(f"Error with SQL connection: {str(e)}")
            raise
        finally:
            # Return connection to pool
            if conn:
                try:
                    if len(self._sql_pool) < self.sql_pool_size:
                        self._sql_pool.append(conn)
                    else:
                        conn.close()
                except Exception as e:
                    self.logger.error(f"Error returning connection to pool: {str(e)}")
    
    async def get_redis_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        if not self._redis_pool:
            await self._init_redis_pool()
        
        return redis.Redis(connection_pool=self._redis_pool)
    
    def get_blob_client(self) -> BlobServiceClient:
        """Get Blob Storage client"""
        if not self._blob_client:
            self._init_azure_clients()
        return self._blob_client
    
    def get_data_lake_client(self) -> DataLakeServiceClient:
        """Get Data Lake client"""
        if not self._data_lake_client:
            self._init_azure_clients()
        return self._data_lake_client
    
    def get_event_hub_producer(self) -> EventHubProducerClient:
        """Get Event Hub producer"""
        if not self._event_hub_producer:
            self._init_azure_clients()
        return self._event_hub_producer
    
    def get_service_bus_client(self) -> ServiceBusClient:
        """Get Service Bus client"""
        if not self._service_bus_client:
            self._init_azure_clients()
        return self._service_bus_client
    
    async def close_all_pools(self):
        """Close all connection pools"""
        try:
            # Close SQL connections
            if self._sql_pool:
                for conn in self._sql_pool:
                    try:
                        conn.close()
                    except Exception as e:
                        self.logger.error(f"Error closing SQL connection: {str(e)}")
                self._sql_pool.clear()
            
            # Close Redis pool
            if self._redis_pool:
                await self._redis_pool.disconnect()
            
            # Close Azure clients
            if self._event_hub_producer:
                await self._event_hub_producer.close()
            
            if self._service_bus_client:
                await self._service_bus_client.close()
            
            self.logger.info("All connection pools closed")
            
        except Exception as e:
            self.logger.error(f"Error closing connection pools: {str(e)}")

# Global connection pool manager
connection_pool = ConnectionPoolManager()