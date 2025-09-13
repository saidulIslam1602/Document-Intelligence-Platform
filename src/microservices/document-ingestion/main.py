"""
Document Ingestion Microservice
Handles document upload, validation, and initial processing
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiofiles
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import json
from azure.storage.blob import BlobServiceClient
from azure.eventhub import EventHubProducerClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import (
    DocumentUploadedEvent, EventBus, EventType
)
from ...shared.storage.data_lake_service import DataLakeService
from ...shared.storage.sql_service import SQLService
from ...shared.cache.redis_cache import cache_service, cache_result, cache_invalidate, CacheKeys
from ...shared.monitoring.performance_monitor import monitor_performance

# Initialize FastAPI app
app = FastAPI(
    title="Document Ingestion Service",
    description="Microservice for document upload and initial processing",
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

# Security
security = HTTPBearer()

# Global variables
config = config_manager.get_azure_config()
event_bus = EventBus()
logger = logging.getLogger(__name__)

# Initialize storage services
data_lake_service = DataLakeService(config.data_lake_connection_string)
sql_service = SQLService(config.sql_connection_string)

# Azure clients
blob_service_client = BlobServiceClient.from_connection_string(
    config.storage_connection_string
)
event_hub_producer = EventHubProducerClient.from_connection_string(
    config.event_hub_connection_string,
    eventhub_name="document-processing"
)
service_bus_client = ServiceBusClient.from_connection_string(
    config.service_bus_connection_string
)

# Pydantic models
class DocumentUploadRequest(BaseModel):
    user_id: str = Field(..., description="User ID uploading the document")
    document_type: Optional[str] = Field(None, description="Expected document type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    processing_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Processing configuration options"
    )

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str
    message: str
    upload_url: Optional[str] = None
    processing_estimated_duration: Optional[int] = None

class DocumentStatus(BaseModel):
    document_id: str
    status: str
    progress: float
    created_at: datetime
    updated_at: datetime
    file_name: str
    file_size: int
    processing_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class BatchUploadRequest(BaseModel):
    user_id: str
    documents: List[Dict[str, Any]]
    batch_processing: bool = True

class BatchUploadResponse(BaseModel):
    batch_id: str
    total_documents: int
    successful_uploads: int
    failed_uploads: int
    document_ids: List[str]

# Dependency injection
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token"""
    # In production, this would validate the JWT token
        # Get actual user ID from authentication
    return "user_123"

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "document-ingestion",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Document upload endpoint
@app.post("/documents/upload", response_model=DocumentUploadResponse)
@monitor_performance("document_upload", {"service": "document-ingestion"})
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    document_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    processing_options: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload a single document for processing"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        file_content = await file.read()
        file_size = len(file_content)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {max_size} bytes"
            )
        
        # Check file type
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.tiff']
        file_extension = '.' + file.filename.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed types: {allowed_extensions}"
            )
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Upload to blob storage
        blob_name = f"documents/{user_id}/{document_id}/{file.filename}"
        blob_client = blob_service_client.get_blob_client(
            container="documents", 
            blob=blob_name
        )
        
        await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: blob_client.upload_blob(file_content, overwrite=True)
        )
        
        # Create document record in SQL Database
        document_record = {
            "document_id": document_id,
            "user_id": user_id,
            "file_name": file.filename,
            "file_size": file_size,
            "content_type": file.content_type,
            "blob_path": blob_name,
            "document_type": document_type,
            "metadata": json.dumps(metadata or {}),
            "processing_options": json.dumps(processing_options or {}),
            "status": "uploaded"
        }
        
        try:
            sql_service.store_document(document_record)
            logger.info(f"Document {document_id} stored in SQL Database")
        except Exception as e:
            logger.error(f"Failed to store document in SQL Database: {str(e)}")
            raise
        
        # Store processing job in SQL Database
        try:
            job_id = sql_service.store_processing_job(
                user_id=user_id,
                document_name=file.filename,
                document_path=blob_name,
                status="uploaded"
            )
            logger.info(f"Processing job {job_id} created for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to create processing job: {str(e)}")
        
        # Store raw data in Data Lake for analytics
        try:
            data_lake_service.store_raw_data(
                data=file_content,
                file_name=f"{document_id}_{file.filename}",
                content_type=file.content_type or "application/octet-stream"
            )
            logger.info(f"Raw data stored in Data Lake for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to store raw data in Data Lake: {str(e)}")
        
        # Publish document uploaded event
        event = DocumentUploadedEvent(
            document_id=document_id,
            file_name=file.filename,
            file_size=file_size,
            content_type=file.content_type,
            user_id=user_id
        )
        
        await publish_event(event)
        
        # Schedule background processing
        background_tasks.add_task(
            schedule_document_processing, 
            document_id, 
            user_id
        )
        
        logger.info(f"Document {document_id} uploaded successfully by user {user_id}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            status="uploaded",
            message="Document uploaded successfully",
            processing_estimated_duration=30  # seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Batch upload endpoint
@app.post("/documents/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_documents(
    request: BatchUploadRequest,
    user_id: str = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload multiple documents in batch"""
    try:
        batch_id = str(uuid.uuid4())
        successful_uploads = 0
        failed_uploads = 0
        document_ids = []
        
        for doc_data in request.documents:
            try:
                # Simulate document upload (in real implementation, files would be uploaded)
                document_id = str(uuid.uuid4())
                
                # Create document record
                document_record = {
                    "id": document_id,
                    "user_id": user_id,
                    "file_name": doc_data.get("file_name", "unknown"),
                    "file_size": doc_data.get("file_size", 0),
                    "content_type": doc_data.get("content_type", "application/octet-stream"),
                    "blob_path": f"documents/{user_id}/{document_id}/{doc_data.get('file_name', 'unknown')}",
                    "document_type": doc_data.get("document_type"),
                    "metadata": doc_data.get("metadata", {}),
                    "processing_options": doc_data.get("processing_options", {}),
                    "status": "uploaded",
                    "batch_id": batch_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "partition_key": user_id
                }
                
                container = database.get_container_client("documents")
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: container.create_item(document_record)
                )
                
                # Publish event
                event = DocumentUploadedEvent(
                    document_id=document_id,
                    file_name=doc_data.get("file_name", "unknown"),
                    file_size=doc_data.get("file_size", 0),
                    content_type=doc_data.get("content_type", "application/octet-stream"),
                    user_id=user_id
                )
                
                await publish_event(event)
                
                document_ids.append(document_id)
                successful_uploads += 1
                
            except Exception as e:
                logger.error(f"Error uploading document in batch: {str(e)}")
                failed_uploads += 1
        
        # Schedule batch processing if requested
        if request.batch_processing and successful_uploads > 0:
            background_tasks.add_task(
                schedule_batch_processing, 
                batch_id, 
                document_ids
            )
        
        logger.info(f"Batch upload completed. Batch ID: {batch_id}, Success: {successful_uploads}, Failed: {failed_uploads}")
        
        return BatchUploadResponse(
            batch_id=batch_id,
            total_documents=len(request.documents),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            document_ids=document_ids
        )
        
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Document status endpoint
@app.get("/documents/{document_id}/status", response_model=DocumentStatus)
async def get_document_status(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get the processing status of a document"""
    try:
        container = database.get_container_client("documents")
        
        # Get document record
        document_record = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.read_item(
                item=document_id,
                partition_key=user_id
            )
        )
        
        # Calculate progress based on status
        progress_map = {
            "uploaded": 10.0,
            "processing": 50.0,
            "analyzed": 80.0,
            "completed": 100.0,
            "failed": 0.0
        }
        
        progress = progress_map.get(document_record.get("status", "uploaded"), 0.0)
        
        return DocumentStatus(
            document_id=document_id,
            status=document_record.get("status", "unknown"),
            progress=progress,
            created_at=datetime.fromisoformat(document_record.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(document_record.get("updated_at", datetime.utcnow().isoformat())),
            file_name=document_record.get("file_name", "unknown"),
            file_size=document_record.get("file_size", 0),
            processing_result=document_record.get("processing_result"),
            error_message=document_record.get("error_message")
        )
        
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# List user documents endpoint
@app.get("/documents")
@cache_result(ttl=300, key_prefix="user_documents")  # Cache for 5 minutes
async def list_user_documents(
    user_id: str = Depends(get_current_user),
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List documents for a user with optional filtering"""
    try:
        # Store in Azure SQL Database
        documents = sql_service.get_user_documents(user_id, limit + offset)
        
        # Apply filters
        if status:
            documents = [doc for doc in documents if doc.get('status') == status]
        if document_type:
            documents = [doc for doc in documents if doc.get('document_type') == document_type]
        
        # Apply pagination
        paginated_docs = documents[offset:offset + limit]
        
        return {
            "documents": paginated_docs,
            "total_count": len(documents),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Delete document endpoint
@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a document and its associated data"""
    try:
        container = database.get_container_client("documents")
        
        # Get document record
        document_record = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.read_item(
                item=document_id,
                partition_key=user_id
            )
        )
        
        # Delete from blob storage
        blob_client = blob_service_client.get_blob_client(
            container="documents",
            blob=document_record.get("blob_path")
        )
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: blob_client.delete_blob()
            )
        except Exception as e:
            logger.warning(f"Could not delete blob: {str(e)}")
        
        # Delete from Azure SQL Database
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.delete_item(
                item=document_id,
                partition_key=user_id
            )
        )
        
        logger.info(f"Document {document_id} deleted by user {user_id}")
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Helper functions
async def publish_event(event: DocumentUploadedEvent):
    """Publish event to Event Hub"""
    try:
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
            "event_data": event.event_data,
            "timestamp": event.timestamp.isoformat(),
            "version": event.version,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id
        }
        
        # Send to Event Hub
        async with event_hub_producer:
            await event_hub_producer.send_batch(
                [{"body": json.dumps(event_data)}],
                partition_key=event.aggregate_id
            )
        
        logger.debug(f"Event {event.event_type.value} published for document {event.aggregate_id}")
        
    except Exception as e:
        logger.error(f"Error publishing event: {str(e)}")
        raise

async def schedule_document_processing(document_id: str, user_id: str):
    """Schedule document for processing"""
    try:
        # Send message to Service Bus queue
        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name="document-processing")
            message = ServiceBusMessage(json.dumps({
                "document_id": document_id,
                "user_id": user_id,
                "scheduled_at": datetime.utcnow().isoformat()
            }))
            await sender.send_messages(message)
        
        logger.info(f"Document {document_id} scheduled for processing")
        
    except Exception as e:
        logger.error(f"Error scheduling document processing: {str(e)}")
        raise

async def schedule_batch_processing(batch_id: str, document_ids: List[str]):
    """Schedule batch processing"""
    try:
        # Send message to Service Bus queue
        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name="batch-processing")
            message = ServiceBusMessage(json.dumps({
                "batch_id": batch_id,
                "document_ids": document_ids,
                "scheduled_at": datetime.utcnow().isoformat()
            }))
            await sender.send_messages(message)
        
        logger.info(f"Batch {batch_id} scheduled for processing with {len(document_ids)} documents")
        
    except Exception as e:
        logger.error(f"Error scheduling batch processing: {str(e)}")
        raise

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Document Ingestion Service started")
    
    # Initialize event bus
    # In production, this would set up proper event handlers
    
    # Create required containers if they don't exist
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: database.create_container_if_not_exists(
                id="documents",
                partition_key="/partition_key"
            )
        )
    except Exception as e:
        logger.warning(f"Could not create documents container: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Document Ingestion Service shutting down")
    
    # Close connections
    await event_hub_producer.close()
    await service_bus_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)