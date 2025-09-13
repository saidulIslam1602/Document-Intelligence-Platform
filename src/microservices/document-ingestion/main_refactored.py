"""
Refactored Document Ingestion Microservice
Uses centralized services to eliminate redundant code
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import centralized services
from ...shared.auth.auth_service import get_current_user_id, User
from ...shared.utils.error_handler import handle_validation_error, ErrorHandler
from ...shared.services.document_service import document_service, DocumentMetadata

# Initialize FastAPI app
app = FastAPI(
    title="Document Ingestion Service (Refactored)",
    description="Microservice for document upload and initial processing - using centralized services",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
logger = logging.getLogger(__name__)

# Pydantic models
class DocumentUploadRequest(BaseModel):
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
    processing_estimated_duration: int = 30

class BatchUploadResponse(BaseModel):
    batch_id: str
    total_documents: int
    successful_uploads: int
    failed_uploads: int
    documents: List[Dict[str, Any]]

# Validation functions
def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file size
    max_size = 50 * 1024 * 1024  # 50MB
    if hasattr(file, 'size') and file.size > max_size:
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

# Document upload endpoint - REFACTORED
@app.post("/documents/upload", response_model=DocumentUploadResponse)
@handle_validation_error("document upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    document_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    processing_options: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload a single document for processing - using centralized document service"""
    try:
        # Validate file
        validate_file(file)
        
        # Read file content
        file_content = await file.read()
        
        # Store document using centralized service
        document_metadata = await document_service.store_document(
            file_content=file_content,
            file_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
            user_id=user_id,
            document_type=document_type,
            metadata=metadata,
            processing_options=processing_options
        )
        
        # Schedule background processing (if needed)
        background_tasks.add_task(
            schedule_document_processing, 
            document_metadata.document_id, 
            user_id
        )
        
        logger.info(f"Document {document_metadata.document_id} uploaded successfully by user {user_id}")
        
        return DocumentUploadResponse(
            document_id=document_metadata.document_id,
            status=document_metadata.status,
            message="Document uploaded successfully",
            processing_estimated_duration=30
        )
        
    except HTTPException:
        raise
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "document upload", 500, "Document upload failed"
        )

# Batch upload endpoint - REFACTORED
@app.post("/documents/batch-upload", response_model=BatchUploadResponse)
@handle_validation_error("batch upload")
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user_id),
    document_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    processing_options: Optional[Dict[str, Any]] = None
):
    """Upload multiple documents in batch - using centralized document service"""
    try:
        import uuid
        batch_id = str(uuid.uuid4())
        
        successful_uploads = 0
        failed_uploads = 0
        documents = []
        
        for file in files:
            try:
                # Validate file
                validate_file(file)
                
                # Read file content
                file_content = await file.read()
                
                # Store document using centralized service
                document_metadata = await document_service.store_document(
                    file_content=file_content,
                    file_name=file.filename,
                    content_type=file.content_type or "application/octet-stream",
                    user_id=user_id,
                    document_type=document_type,
                    metadata=metadata,
                    processing_options=processing_options
                )
                
                documents.append({
                    "document_id": document_metadata.document_id,
                    "file_name": document_metadata.file_name,
                    "status": document_metadata.status
                })
                
                successful_uploads += 1
                
            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {str(e)}")
                failed_uploads += 1
                documents.append({
                    "file_name": file.filename,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"Batch upload {batch_id} completed: {successful_uploads} successful, {failed_uploads} failed")
        
        return BatchUploadResponse(
            batch_id=batch_id,
            total_documents=len(files),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            documents=documents
        )
        
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "batch upload", 500, "Batch upload failed"
        )

# Document status endpoint - REFACTORED
@app.get("/documents/{document_id}/status")
@handle_validation_error("get document status")
async def get_document_status(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get document processing status - using centralized services"""
    try:
        # This would typically query the centralized document service
        # For now, return a placeholder response
        return {
            "document_id": document_id,
            "status": "processing",
            "message": "Document status retrieved successfully"
        }
        
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "get document status", 500, "Failed to get document status"
        )

# Background task
async def schedule_document_processing(document_id: str, user_id: str):
    """Schedule document processing - placeholder for actual processing logic"""
    try:
        logger.info(f"Scheduling processing for document {document_id}")
        
        # Simulate processing delay
        await asyncio.sleep(2)
        
        # Update document status
        await document_service.update_document_status(
            document_id=document_id,
            status="processing",
            processing_metadata={"processing_started": datetime.utcnow().isoformat()}
        )
        
        # Simulate more processing
        await asyncio.sleep(5)
        
        # Mark as completed
        await document_service.update_document_status(
            document_id=document_id,
            status="completed",
            processing_metadata={"processing_completed": datetime.utcnow().isoformat()}
        )
        
        logger.info(f"Document {document_id} processing completed")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        
        # Mark as failed
        await document_service.update_document_status(
            document_id=document_id,
            status="failed",
            error_message=str(e)
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "document-ingestion-refactored"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Refactored Document Ingestion Service started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Refactored Document Ingestion Service stopped")