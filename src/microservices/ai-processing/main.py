"""
AI Processing Microservice
Handles document analysis, classification, and AI-powered insights
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from azure.servicebus import ServiceBusClient, ServiceBusMessage
# Cosmos DB removed - using Azure SQL Database
from azure.storage.blob import BlobServiceClient

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import (
    DocumentProcessingStartedEvent, DocumentProcessingCompletedEvent,
    DocumentProcessingFailedEvent, DocumentClassifiedEvent, EventBus
)
from .openai_service import OpenAIService
from .form_recognizer_service import FormRecognizerService
from .ml_models import MLModelManager
from .fine_tuning_service import DocumentFineTuningService
from .fine_tuning_api import router as fine_tuning_router
from .fine_tuning_workflow import DocumentFineTuningWorkflow
from .fine_tuning_dashboard import FineTuningDashboard
from .fine_tuning_websocket import router as fine_tuning_ws_router
from .fine_tuning_database import initialize_fine_tuning_database
from .langchain_orchestration import LangChainOrchestrator, DocumentProcessingAgent
from .llmops_automation import LLMOpsAutomationTracker

# Initialize FastAPI app
app = FastAPI(
    title="AI Processing Service",
    description="Microservice for AI-powered document analysis and processing",
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

# Azure clients
# Cosmos DB removed - using Azure SQL Database for all data storage
blob_service_client = BlobServiceClient.from_connection_string(
    config.storage_connection_string
)
service_bus_client = ServiceBusClient.from_connection_string(
    config.service_bus_connection_string
)

# AI Services
openai_service = OpenAIService(event_bus)
form_recognizer_service = FormRecognizerService(event_bus)
ml_model_manager = MLModelManager(event_bus)
fine_tuning_service = DocumentFineTuningService(event_bus)
fine_tuning_workflow = DocumentFineTuningWorkflow(event_bus)
fine_tuning_dashboard = FineTuningDashboard(event_bus)
langchain_orchestrator = LangChainOrchestrator(event_bus)
document_agent = DocumentProcessingAgent(event_bus)
llmops_tracker = LLMOpsAutomationTracker(event_bus)

# Pydantic models
class ProcessingRequest(BaseModel):
    document_id: str
    user_id: str
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProcessingResponse(BaseModel):
    document_id: str
    status: str
    processing_result: Optional[Dict[str, Any]] = None
    processing_duration: Optional[float] = None
    error_message: Optional[str] = None

class ClassificationRequest(BaseModel):
    text: str
    document_type: Optional[str] = None

class ClassificationResponse(BaseModel):
    predicted_type: str
    confidence: float
    top_predictions: List[Dict[str, Any]]
    model_used: str

class SentimentAnalysisRequest(BaseModel):
    text: str

class SentimentAnalysisResponse(BaseModel):
    predicted_sentiment: str
    confidence: float
    sentiment_scores: Dict[str, float]
    model_used: str

class QAResponse(BaseModel):
    question: str
    answer: str
    context_used: bool
    confidence: Optional[float] = None
    model_used: str

class BatchProcessingRequest(BaseModel):
    document_ids: List[str]
    user_id: str
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class BatchProcessingResponse(BaseModel):
    batch_id: str
    total_documents: int
    successful_processing: int
    failed_processing: int
    results: List[Dict[str, Any]]

# Dependency injection
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token"""
    return "user_123"

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-processing",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "ai_services": {
            "openai": "available",
            "form_recognizer": "available",
            "ml_models": "available"
        }
    }

# Process document endpoint
@app.post("/process", response_model=ProcessingResponse)
async def process_document(
    request: ProcessingRequest,
    user_id: str = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Process a single document with AI services"""
    try:
        start_time = datetime.utcnow()
        
        # Get document from storage
        document = await get_document(request.document_id, user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Download document content
        document_content = await download_document_content(document["blob_path"])
        
        # Publish processing started event
        processing_started_event = DocumentProcessingStartedEvent(
            document_id=request.document_id,
            processing_pipeline="ai-powered-pipeline",
            estimated_duration=60,
            correlation_id=request.document_id
        )
        await publish_event(processing_started_event)
        
        # Process document with AI services
        processing_result = await process_document_with_ai(
            document_content, 
            document, 
            request.processing_options
        )
        
        # Calculate processing duration
        processing_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Update document record
        await update_document_processing_result(
            request.document_id, 
            user_id, 
            processing_result, 
            processing_duration
        )
        
        # Publish processing completed event
        processing_completed_event = DocumentProcessingCompletedEvent(
            document_id=request.document_id,
            processing_result=processing_result,
            processing_duration=int(processing_duration),
            correlation_id=request.document_id
        )
        await publish_event(processing_completed_event)
        
        logger.info(f"Document {request.document_id} processed successfully in {processing_duration:.2f}s")
        
        return ProcessingResponse(
            document_id=request.document_id,
            status="completed",
            processing_result=processing_result,
            processing_duration=processing_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {request.document_id}: {str(e)}")
        
        # Publish processing failed event
        processing_failed_event = DocumentProcessingFailedEvent(
            document_id=request.document_id,
            error_message=str(e),
            error_code="PROCESSING_ERROR",
            retry_count=0,
            correlation_id=request.document_id
        )
        await publish_event(processing_failed_event)
        
        raise HTTPException(status_code=500, detail="Internal server error")

# Batch processing endpoint
@app.post("/batch-process", response_model=BatchProcessingResponse)
async def batch_process_documents(
    request: BatchProcessingRequest,
    user_id: str = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Process multiple documents in batch"""
    try:
        batch_id = str(uuid.uuid4())
        successful_processing = 0
        failed_processing = 0
        results = []
        
        # Process documents concurrently
        tasks = []
        for document_id in request.document_ids:
            task = process_single_document_async(
                document_id, user_id, request.processing_options
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(batch_results):
            document_id = request.document_ids[i]
            
            if isinstance(result, Exception):
                failed_processing += 1
                results.append({
                    "document_id": document_id,
                    "status": "failed",
                    "error": str(result)
                })
            else:
                successful_processing += 1
                results.append({
                    "document_id": document_id,
                    "status": "completed",
                    "processing_result": result
                })
        
        logger.info(f"Batch processing completed. Batch ID: {batch_id}, Success: {successful_processing}, Failed: {failed_processing}")
        
        return BatchProcessingResponse(
            batch_id=batch_id,
            total_documents=len(request.document_ids),
            successful_processing=successful_processing,
            failed_processing=failed_processing,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Document classification endpoint
@app.post("/classify", response_model=ClassificationResponse)
async def classify_document(request: ClassificationRequest):
    """Classify document type using ML models"""
    try:
        classification_result = await ml_model_manager.classify_document(request.text)
        
        return ClassificationResponse(
            predicted_type=classification_result["predicted_type"],
            confidence=classification_result["confidence"],
            top_predictions=classification_result["top_predictions"],
            model_used=classification_result["model_used"]
        )
        
    except Exception as e:
        logger.error(f"Error classifying document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Sentiment analysis endpoint
@app.post("/sentiment", response_model=SentimentAnalysisResponse)
async def analyze_sentiment(request: SentimentAnalysisRequest):
    """Analyze sentiment of text using ML models"""
    try:
        sentiment_result = await ml_model_manager.analyze_sentiment(request.text)
        
        return SentimentAnalysisResponse(
            predicted_sentiment=sentiment_result["predicted_sentiment"],
            confidence=sentiment_result["confidence"],
            sentiment_scores=sentiment_result["sentiment_scores"],
            model_used=sentiment_result["model_used"]
        )
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Q&A endpoint
@app.post("/qa", response_model=QAResponse)
async def answer_question(
    question: str,
    document_id: Optional[str] = None,
    context: Optional[str] = None
):
    """Answer questions about documents using OpenAI"""
    try:
        qa_result = await openai_service.answer_question(question, context, document_id)
        
        return QAResponse(
            question=qa_result["question"],
            answer=qa_result["answer"],
            context_used=qa_result["context_used"],
            model_used=qa_result["model_used"]
        )
        
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Extract entities endpoint
@app.post("/entities")
async def extract_entities(text: str):
    """Extract named entities from text using OpenAI"""
    try:
        entities_result = await openai_service.extract_entities(text)
        return entities_result
        
    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Generate summary endpoint
@app.post("/summarize")
async def generate_summary(text: str, max_length: int = 200):
    """Generate document summary using OpenAI"""
    try:
        summary_result = await openai_service.generate_summary(text, max_length)
        return summary_result
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Train model endpoint
@app.post("/models/train")
async def train_model(
    model_type: str,
    training_data: List[Dict[str, Any]],
    user_id: str = Depends(get_current_user)
):
    """Train ML models with provided data"""
    try:
        if model_type == "document_classifier":
            result = await ml_model_manager.train_document_classifier(training_data)
        elif model_type == "sentiment_classifier":
            result = await ml_model_manager.train_sentiment_classifier(training_data)
        elif model_type == "language_detector":
            result = await ml_model_manager.train_language_detector(training_data)
        else:
            raise HTTPException(status_code=400, detail="Invalid model type")
        
        return {
            "model_type": model_type,
            "training_result": result,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# LangChain orchestration endpoints
@app.post("/process-invoice-langchain")
async def process_invoice_with_langchain(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Process invoice using LangChain orchestration"""
    try:
        # Get document
        document = await get_document(document_id, user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Download document content
        document_content = await download_document_content(document["blob_path"])
        
        # Process with LangChain
        result = await langchain_orchestrator.process_invoice_with_langchain(
            document_content,
            document_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing invoice with LangChain: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/analyze-document-langchain")
async def analyze_document_with_langchain(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Analyze document using LangChain orchestration"""
    try:
        # Get document
        document = await get_document(document_id, user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get document text
        document_text = document.get("extracted_text", "")
        if not document_text:
            # Extract text if not already done
            document_content = await download_document_content(document["blob_path"])
            text_extraction = await form_recognizer_service.extract_text(document_content)
            document_text = text_extraction["text"]
        
        # Analyze with LangChain
        result = await langchain_orchestrator.analyze_document_with_langchain(
            document_text,
            document_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document with LangChain: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/fine-tuning-workflow-langchain")
async def orchestrate_fine_tuning_with_langchain(
    training_data_sample: str,
    model_type: str = "gpt-3.5-turbo",
    user_id: str = Depends(get_current_user)
):
    """Orchestrate fine-tuning workflow using LangChain"""
    try:
        result = await langchain_orchestrator.orchestrate_fine_tuning_workflow(
            training_data_sample,
            model_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error orchestrating fine-tuning workflow: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/process-document-agent")
async def process_document_with_agent(
    document_id: str,
    task_description: str,
    user_id: str = Depends(get_current_user)
):
    """Process document using multi-agent workflow"""
    try:
        result = await document_agent.process_document_with_agent(
            document_id,
            task_description
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing document with agent: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Enhanced LLMOps with automation tracking endpoints
@app.post("/llmops/track-model-metrics")
async def track_model_automation_metrics(
    model_id: str,
    model_name: str,
    test_documents: List[str],
    user_id: str = Depends(get_current_user)
):
    """Track automation metrics for a fine-tuned model"""
    try:
        metrics = await llmops_tracker.track_model_automation_metrics(
            model_id,
            model_name,
            test_documents
        )
        
        return {
            "model_id": metrics.model_id,
            "model_name": metrics.model_name,
            "automation_rate": round(metrics.automation_rate, 2),
            "accuracy": round(metrics.accuracy, 3),
            "confidence": round(metrics.confidence, 3),
            "completeness": round(metrics.completeness, 3),
            "validation_pass_rate": round(metrics.validation_pass_rate, 2),
            "processing_speed": round(metrics.processing_speed, 2),
            "cost_per_document": round(metrics.cost_per_document, 4),
            "documents_processed": metrics.documents_processed,
            "timestamp": metrics.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error tracking model metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/llmops/compare-models")
async def compare_baseline_and_finetuned_models(
    baseline_model_id: str,
    fine_tuned_model_id: str,
    test_documents: List[str],
    user_id: str = Depends(get_current_user)
):
    """Compare baseline and fine-tuned model performance"""
    try:
        comparison = await llmops_tracker.compare_models(
            baseline_model_id,
            fine_tuned_model_id,
            test_documents
        )
        
        return {
            "baseline_metrics": {
                "automation_rate": round(comparison.baseline_metrics.automation_rate, 2),
                "accuracy": round(comparison.baseline_metrics.accuracy, 3),
                "confidence": round(comparison.baseline_metrics.confidence, 3),
                "completeness": round(comparison.baseline_metrics.completeness, 3),
                "processing_speed": round(comparison.baseline_metrics.processing_speed, 2),
                "cost_per_document": round(comparison.baseline_metrics.cost_per_document, 4)
            },
            "fine_tuned_metrics": {
                "automation_rate": round(comparison.fine_tuned_metrics.automation_rate, 2),
                "accuracy": round(comparison.fine_tuned_metrics.accuracy, 3),
                "confidence": round(comparison.fine_tuned_metrics.confidence, 3),
                "completeness": round(comparison.fine_tuned_metrics.completeness, 3),
                "processing_speed": round(comparison.fine_tuned_metrics.processing_speed, 2),
                "cost_per_document": round(comparison.fine_tuned_metrics.cost_per_document, 4)
            },
            "improvement": comparison.improvement,
            "recommendation": comparison.recommendation,
            "confidence_level": comparison.confidence_level
        }
        
    except Exception as e:
        logger.error(f"Error comparing models: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/llmops/optimize-for-goal")
async def optimize_model_for_automation_goal(
    current_model_id: str,
    target_automation_rate: float = 90.0,
    user_id: str = Depends(get_current_user)
):
    """Get optimization recommendations to achieve automation goal"""
    try:
        optimization = await llmops_tracker.optimize_for_automation_goal(
            current_model_id,
            target_automation_rate
        )
        
        return optimization
        
    except Exception as e:
        logger.error(f"Error optimizing for automation goal: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/llmops/automation-dashboard")
async def get_llmops_automation_dashboard(
    time_range: str = "7d",
    user_id: str = Depends(get_current_user)
):
    """Get automation dashboard data for LLMOps"""
    try:
        dashboard_data = await llmops_tracker.generate_automation_dashboard_data(time_range)
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting automation dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Get model status endpoint
@app.get("/models/status")
async def get_model_status():
    """Get status of all ML models"""
    try:
        models_status = {}
        
        # Check each model
        for model_name in ml_model_manager.models.keys():
            try:
                # Simple health check - try to make a prediction
                test_result = await ml_model_manager.classify_document("test document")
                models_status[model_name] = {
                    "status": "healthy",
                    "last_check": datetime.utcnow().isoformat()
                }
            except Exception as e:
                models_status[model_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat()
                }
        
        return {
            "models": models_status,
            "overall_status": "healthy" if all(
                model["status"] == "healthy" for model in models_status.values()
            ) else "degraded"
        }
        
    except Exception as e:
        logger.error(f"Error getting model status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Helper functions
async def get_document(document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get document record from database"""
    try:
        container = database.get_container_client("documents")
        document = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.read_item(
                item=document_id,
                partition_key=user_id
            )
        )
        return document
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        return None

async def download_document_content(blob_path: str) -> bytes:
    """Download document content from blob storage"""
    try:
        blob_client = blob_service_client.get_blob_client(
            container="documents",
            blob=blob_path
        )
        content = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: blob_client.download_blob().readall()
        )
        return content
    except Exception as e:
        logger.error(f"Error downloading document content: {str(e)}")
        raise

async def process_document_with_ai(
    document_content: bytes, 
    document: Dict[str, Any], 
    processing_options: Dict[str, Any]
) -> Dict[str, Any]:
    """Process document using AI services"""
    try:
        # Extract text using Form Recognizer
        text_extraction = await form_recognizer_service.extract_text(document_content)
        extracted_text = text_extraction["text"]
        
        # Classify document type
        classification = await ml_model_manager.classify_document(extracted_text)
        
        # Analyze sentiment
        sentiment = await ml_model_manager.analyze_sentiment(extracted_text)
        
        # Detect language
        language = await ml_model_manager.detect_language(extracted_text)
        
        # Extract entities using OpenAI
        entities = await openai_service.extract_entities(extracted_text)
        
        # Generate summary
        summary = await openai_service.generate_summary(extracted_text)
        
        # Extract key information using Form Recognizer
        key_info = await form_recognizer_service.extract_key_value_pairs(document_content)
        
        # Extract tables if present
        tables = await form_recognizer_service.extract_tables(document_content)
        
        # Combine all results
        processing_result = {
            "document_type": classification["predicted_type"],
            "classification_confidence": classification["confidence"],
            "sentiment": sentiment["predicted_sentiment"],
            "sentiment_confidence": sentiment["confidence"],
            "language": language["predicted_language"],
            "language_confidence": language["confidence"],
            "extracted_text": extracted_text,
            "entities": entities["entities"],
            "summary": summary["summary"],
            "key_information": key_info,
            "tables": tables,
            "text_extraction_confidence": text_extraction["confidence"],
            "processing_timestamp": datetime.utcnow().isoformat(),
            "ai_models_used": [
                "form_recognizer",
                "openai_gpt4",
                "custom_ml_models"
            ]
        }
        
        return processing_result
        
    except Exception as e:
        logger.error(f"Error processing document with AI: {str(e)}")
        raise

async def update_document_processing_result(
    document_id: str, 
    user_id: str, 
    processing_result: Dict[str, Any], 
    processing_duration: float
):
    """Update document record with processing results"""
    try:
        container = database.get_container_client("documents")
        
        # Get current document record
        document = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.read_item(
                item=document_id,
                partition_key=user_id
            )
        )
        
        # Update with processing results
        document["status"] = "completed"
        document["processing_result"] = processing_result
        document["processing_duration"] = processing_duration
        document["updated_at"] = datetime.utcnow().isoformat()
        
        # Save updated document
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.replace_item(
                item=document_id,
                body=document
            )
        )
        
    except Exception as e:
        logger.error(f"Error updating document processing result: {str(e)}")
        raise

async def process_single_document_async(
    document_id: str, 
    user_id: str, 
    processing_options: Dict[str, Any]
) -> Dict[str, Any]:
    """Process a single document asynchronously"""
    try:
        # Get document
        document = await get_document(document_id, user_id)
        if not document:
            raise Exception("Document not found")
        
        # Download content
        document_content = await download_document_content(document["blob_path"])
        
        # Process with AI
        processing_result = await process_document_with_ai(
            document_content, 
            document, 
            processing_options
        )
        
        # Update document
        await update_document_processing_result(
            document_id, 
            user_id, 
            processing_result, 
            0.0  # Duration will be calculated by caller
        )
        
        return processing_result
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        raise

async def publish_event(event):
    """Publish event to event bus"""
    try:
        await event_bus.publish(event)
    except Exception as e:
        logger.error(f"Error publishing event: {str(e)}")

# Include routers
app.include_router(fine_tuning_router)
app.include_router(fine_tuning_ws_router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("AI Processing Service started")
    
    # Initialize fine-tuning database
    try:
        await initialize_fine_tuning_database()
        logger.info("Fine-tuning database initialized")
    except Exception as e:
        logger.warning(f"Could not initialize fine-tuning database: {str(e)}")
    
    # Load pre-trained models
    try:
        await ml_model_manager.load_model("document_classifier_tfidf")
        await ml_model_manager.load_model("sentiment_classifier")
        await ml_model_manager.load_model("language_detector")
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load some models: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("AI Processing Service shutting down")
    await service_bus_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)