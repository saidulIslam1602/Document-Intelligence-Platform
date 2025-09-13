"""
Centralized Document Management Service
Eliminates duplicate document storage logic across microservices
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from ..config.settings import config_manager
from ..storage.data_lake_service import DataLakeService
from ..storage.sql_service import SQLService
from ..events.event_sourcing import DocumentUploadedEvent, EventBus

@dataclass
class DocumentMetadata:
    """Document metadata model"""
    document_id: str
    user_id: str
    file_name: str
    file_size: int
    content_type: str
    blob_path: str
    document_type: Optional[str] = None
    metadata: Dict[str, Any] = None
    processing_options: Dict[str, Any] = None
    status: str = "uploaded"
    created_at: str = None
    updated_at: str = None

class DocumentService:
    """Centralized document management service"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize storage services
        self.data_lake_service = DataLakeService(self.config.data_lake_connection_string)
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.event_bus = EventBus()
        
        # Azure clients
        from azure.storage.blob import BlobServiceClient
        # Cosmos DB removed - using Azure SQL Database
        
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.config.storage_connection_string
        )
        # Cosmos DB removed - all data stored in Azure SQL Database
    
    async def store_document(
        self, 
        file_content: bytes,
        file_name: str,
        content_type: str,
        user_id: str,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> DocumentMetadata:
        """Store document across all storage systems"""
        try:
            # Generate document ID
            import uuid
            document_id = str(uuid.uuid4())
            
            # Create blob path
            blob_name = f"documents/{user_id}/{document_id}/{file_name}"
            
            # Upload to blob storage
            blob_client = self.blob_service_client.get_blob_client(
                container="documents", 
                blob=blob_name
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: blob_client.upload_blob(file_content, overwrite=True)
            )
            
            # Create document metadata
            now = datetime.utcnow().isoformat()
            document_metadata = DocumentMetadata(
                document_id=document_id,
                user_id=user_id,
                file_name=file_name,
                file_size=len(file_content),
                content_type=content_type,
                blob_path=blob_name,
                document_type=document_type,
                metadata=metadata or {},
                processing_options=processing_options or {},
                status="uploaded",
                created_at=now,
                updated_at=now
            )
            
        # Store metadata in Azure SQL Database
        await self._store_sql_metadata(document_metadata)
            
            # Store processing job in SQL Database
            await self._store_sql_job(document_metadata)
            
            # Store raw data in Data Lake
            await self._store_data_lake_raw_data(document_metadata, file_content)
            
            # Publish event
            await self._publish_upload_event(document_metadata)
            
            self.logger.info(f"Document {document_id} stored successfully across all systems")
            return document_metadata
            
        except Exception as e:
            self.logger.error(f"Error storing document: {str(e)}")
            raise
    
    async def _store_sql_metadata(self, metadata: DocumentMetadata):
        """Store document metadata in Azure SQL Database"""
        try:
            query = """
            INSERT INTO documents 
            (document_id, user_id, file_name, file_size, content_type, blob_path, 
             document_type, metadata, processing_options, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                metadata.document_id,
                metadata.user_id,
                metadata.file_name,
                metadata.file_size,
                metadata.content_type,
                metadata.blob_path,
                metadata.document_type,
                json.dumps(metadata.metadata) if metadata.metadata else None,
                json.dumps(metadata.processing_options) if metadata.processing_options else None,
                metadata.status,
                metadata.created_at,
                metadata.updated_at
            )
            
            await self.sql_service.execute_non_query(query, params)
            self.logger.info(f"Document metadata stored in SQL Database: {metadata.document_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store SQL metadata: {str(e)}")
            raise
    
    async def _store_sql_job(self, metadata: DocumentMetadata):
        """Store processing job in SQL Database"""
        try:
            job_id = self.sql_service.store_processing_job(
                user_id=metadata.user_id,
                document_name=metadata.file_name,
                document_path=metadata.blob_path,
                status=metadata.status
            )
            self.logger.info(f"Processing job {job_id} created for document {metadata.document_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create SQL job: {str(e)}")
            # Don't raise - this is not critical for document storage
    
    async def _store_data_lake_raw_data(self, metadata: DocumentMetadata, file_content: bytes):
        """Store raw data in Data Lake"""
        try:
            self.data_lake_service.store_raw_data(
                data=file_content,
                file_name=f"{metadata.document_id}_{metadata.file_name}",
                content_type=metadata.content_type
            )
            self.logger.info(f"Raw data stored in Data Lake for document {metadata.document_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store Data Lake raw data: {str(e)}")
            # Don't raise - this is not critical for document storage
    
    async def _publish_upload_event(self, metadata: DocumentMetadata):
        """Publish document uploaded event"""
        try:
            event = DocumentUploadedEvent(
                document_id=metadata.document_id,
                file_name=metadata.file_name,
                file_size=metadata.file_size,
                content_type=metadata.content_type,
                user_id=metadata.user_id
            )
            
            await self.event_bus.publish(event)
            
        except Exception as e:
            self.logger.error(f"Failed to publish upload event: {str(e)}")
            # Don't raise - this is not critical for document storage
    
    async def update_document_status(
        self, 
        document_id: str, 
        status: str,
        error_message: Optional[str] = None,
        processing_metadata: Optional[Dict[str, Any]] = None
    ):
        """Update document status across all systems"""
        try:
        # Update SQL Database
        await self._update_sql_status(document_id, status, error_message, processing_metadata)
            
            # Update SQL Database
            await self._update_sql_status(document_id, status, error_message, processing_metadata)
            
            self.logger.info(f"Document {document_id} status updated to {status}")
            
        except Exception as e:
            self.logger.error(f"Error updating document status: {str(e)}")
            raise
    
    async def _update_sql_status(
        self, 
        document_id: str, 
        status: str,
        error_message: Optional[str] = None,
        processing_metadata: Optional[Dict[str, Any]] = None
    ):
        """Update status in Azure SQL Database"""
        try:
            query = """
            UPDATE documents 
            SET status = ?, updated_at = ?, error_message = ?, processing_metadata = ?
            WHERE document_id = ?
            """
            
            params = (
                status,
                datetime.utcnow(),
                error_message,
                json.dumps(processing_metadata) if processing_metadata else None,
                document_id
            )
            
            await self.sql_service.execute_non_query(query, params)
            self.logger.info(f"Document {document_id} status updated in SQL Database")
            
        except Exception as e:
            self.logger.error(f"Failed to update SQL status: {str(e)}")
            raise
    

# Global document service instance
document_service = DocumentService()