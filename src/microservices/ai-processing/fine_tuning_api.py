"""
Fine-Tuning API Endpoints
REST API for managing fine-tuning operations
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from enum import Enum

from .fine_tuning_service import DocumentFineTuningService, FineTuningStatus, FineTuningMethod
from src.shared.auth.auth_service import AuthService
from src.shared.monitoring.performance_monitor import performance_monitor

router = APIRouter(prefix="/api/v1/fine-tuning", tags=["Fine-Tuning"])
logger = logging.getLogger(__name__)

# Initialize services
fine_tuning_service = DocumentFineTuningService()
auth_service = AuthService()

# Pydantic models
class FineTuningJobRequest(BaseModel):
    """Request model for creating fine-tuning job"""
    model_name: str = Field(..., description="Model to fine-tune (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)")
    document_type: str = Field(..., description="Type of documents to train on")
    industry: str = Field(..., description="Industry domain")
    min_samples: int = Field(50, description="Minimum number of training samples")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Custom hyperparameters")
    suffix: Optional[str] = Field(None, description="Suffix for model name")
    validation_split: float = Field(0.2, description="Validation data split ratio")

class FineTuningJobResponse(BaseModel):
    """Response model for fine-tuning job"""
    job_id: str
    model_name: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    fine_tuned_model: Optional[str]
    training_tokens: Optional[int]
    error_message: Optional[str]

class ModelEvaluationRequest(BaseModel):
    """Request model for evaluating fine-tuned model"""
    model_name: str = Field(..., description="Fine-tuned model name")
    test_documents: List[Dict[str, Any]] = Field(..., description="Test documents for evaluation")

class ModelEvaluationResponse(BaseModel):
    """Response model for model evaluation"""
    model_name: str
    total_documents: int
    accuracy: float
    average_confidence: float
    document_type_accuracy: Dict[str, Any]
    industry_accuracy: Dict[str, Any]
    evaluation_timestamp: datetime

class CostEstimateRequest(BaseModel):
    """Request model for cost estimation"""
    model_name: str = Field(..., description="Model to estimate costs for")
    training_tokens: int = Field(..., description="Number of training tokens")

class CostEstimateResponse(BaseModel):
    """Response model for cost estimation"""
    model_name: str
    training_tokens: int
    training_cost: float
    hosting_cost_per_hour: float
    estimated_training_hours: int
    estimated_total_cost: float

class DeployModelRequest(BaseModel):
    """Request model for deploying fine-tuned model"""
    model_name: str = Field(..., description="Fine-tuned model name")
    deployment_name: str = Field(..., description="Deployment name")
    deployment_type: str = Field("standard", description="Deployment type")

# Dependency for authentication
async def get_current_user():
    """Get current authenticated user"""
    # This would integrate with your auth service
    return {"user_id": "current_user", "permissions": ["fine_tuning"]}

@router.post("/jobs", response_model=FineTuningJobResponse)
@performance_monitor.monitor_endpoint
async def create_fine_tuning_job(
    request: FineTuningJobRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new fine-tuning job"""
    try:
        logger.info(f"Creating fine-tuning job for {request.model_name} - {request.document_type}")
        
        # Get documents for training
        documents = await _get_training_documents(request.document_type, request.industry)
        
        if len(documents) < request.min_samples:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient training data: {len(documents)} documents, minimum {request.min_samples} required"
            )
        
        # Prepare training data
        training_file_id, validation_file_id = await fine_tuning_service.prepare_training_data(
            documents=documents,
            document_type=request.document_type,
            industry=request.industry,
            min_samples=request.min_samples
        )
        
        # Create fine-tuning job
        job = await fine_tuning_service.create_fine_tuning_job(
            model_name=request.model_name,
            training_file_id=training_file_id,
            validation_file_id=validation_file_id,
            hyperparameters=request.hyperparameters,
            suffix=request.suffix
        )
        
        # Start background monitoring
        background_tasks.add_task(_monitor_job_progress, job.job_id)
        
        return FineTuningJobResponse(
            job_id=job.job_id,
            model_name=job.model_name,
            status=job.status.value,
            created_at=job.created_at,
            finished_at=job.finished_at,
            fine_tuned_model=job.fine_tuned_model,
            training_tokens=job.training_tokens,
            error_message=job.error_message
        )
        
    except Exception as e:
        logger.error(f"Error creating fine-tuning job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[FineTuningJobResponse])
@performance_monitor.monitor_endpoint
async def list_fine_tuning_jobs(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """List all fine-tuning jobs"""
    try:
        jobs = await fine_tuning_service.list_fine_tuning_jobs(limit=limit)
        
        return [
            FineTuningJobResponse(
                job_id=job.job_id,
                model_name=job.model_name,
                status=job.status.value,
                created_at=job.created_at,
                finished_at=job.finished_at,
                fine_tuned_model=job.fine_tuned_model,
                training_tokens=job.training_tokens,
                error_message=job.error_message
            )
            for job in jobs
        ]
        
    except Exception as e:
        logger.error(f"Error listing fine-tuning jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}", response_model=FineTuningJobResponse)
@performance_monitor.monitor_endpoint
async def get_fine_tuning_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific fine-tuning job status"""
    try:
        job = await fine_tuning_service.get_fine_tuning_job(job_id)
        
        return FineTuningJobResponse(
            job_id=job.job_id,
            model_name=job.model_name,
            status=job.status.value,
            created_at=job.created_at,
            finished_at=job.finished_at,
            fine_tuned_model=job.fine_tuned_model,
            training_tokens=job.training_tokens,
            error_message=job.error_message
        )
        
    except Exception as e:
        logger.error(f"Error getting fine-tuning job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
@performance_monitor.monitor_endpoint
async def cancel_fine_tuning_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a fine-tuning job"""
    try:
        success = await fine_tuning_service.cancel_fine_tuning_job(job_id)
        
        if success:
            return {"message": f"Job {job_id} cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")
            
    except Exception as e:
        logger.error(f"Error cancelling fine-tuning job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate", response_model=ModelEvaluationResponse)
@performance_monitor.monitor_endpoint
async def evaluate_model(
    request: ModelEvaluationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Evaluate fine-tuned model performance"""
    try:
        results = await fine_tuning_service.evaluate_fine_tuned_model(
            model_name=request.model_name,
            test_documents=request.test_documents
        )
        
        return ModelEvaluationResponse(
            model_name=results["model_name"],
            total_documents=results["total_documents"],
            accuracy=results["accuracy"],
            average_confidence=results["average_confidence"],
            document_type_accuracy=results["document_type_accuracy"],
            industry_accuracy=results["industry_accuracy"],
            evaluation_timestamp=datetime.fromisoformat(results["evaluation_timestamp"])
        )
        
    except Exception as e:
        logger.error(f"Error evaluating model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deploy")
@performance_monitor.monitor_endpoint
async def deploy_model(
    request: DeployModelRequest,
    current_user: dict = Depends(get_current_user)
):
    """Deploy a fine-tuned model"""
    try:
        deployment_id = await fine_tuning_service.deploy_fine_tuned_model(
            model_name=request.model_name,
            deployment_name=request.deployment_name,
            deployment_type=request.deployment_type
        )
        
        return {
            "message": "Model deployed successfully",
            "deployment_id": deployment_id,
            "model_name": request.model_name,
            "deployment_name": request.deployment_name
        }
        
    except Exception as e:
        logger.error(f"Error deploying model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cost-estimate", response_model=CostEstimateResponse)
@performance_monitor.monitor_endpoint
async def estimate_costs(
    request: CostEstimateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Estimate fine-tuning costs"""
    try:
        estimate = await fine_tuning_service.get_training_cost_estimate(
            model_name=request.model_name,
            training_tokens=request.training_tokens
        )
        
        return CostEstimateResponse(
            model_name=estimate["model_name"],
            training_tokens=estimate["training_tokens"],
            training_cost=estimate["training_cost"],
            hosting_cost_per_hour=estimate["hosting_cost_per_hour"],
            estimated_training_hours=estimate["estimated_training_hours"],
            estimated_total_cost=estimate["estimated_total_cost"]
        )
        
    except Exception as e:
        logger.error(f"Error estimating costs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/supported")
@performance_monitor.monitor_endpoint
async def get_supported_models():
    """Get list of supported models for fine-tuning"""
    try:
        return {
            "supported_models": list(fine_tuning_service.supported_models.keys()),
            "document_types": fine_tuning_service.document_types,
            "industries": fine_tuning_service.industries
        }
        
    except Exception as e:
        logger.error(f"Error getting supported models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/events")
@performance_monitor.monitor_endpoint
async def get_job_events(
    job_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get fine-tuning job events"""
    try:
        # This would integrate with Azure OpenAI events API
        events = await fine_tuning_service.client.fine_tuning.jobs.list_events(
            fine_tuning_job_id=job_id,
            limit=limit
        )
        
        return {
            "job_id": job_id,
            "events": [
                {
                    "id": event.id,
                    "created_at": event.created_at,
                    "level": event.level,
                    "message": event.message,
                    "type": event.type
                }
                for event in events.data
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting job events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _get_training_documents(document_type: str, industry: str) -> List[Dict[str, Any]]:
    """Get training documents from database"""
    try:
        # This would query your document database
        # For now, return mock data
        query = """
        SELECT document_id, extracted_text, document_type, industry, 
               entities, summary, confidence, created_at
        FROM processed_documents 
        WHERE document_type = ? AND industry = ? 
        AND confidence > 0.8
        ORDER BY created_at DESC
        LIMIT 1000
        """
        
        # This would be replaced with actual database query
        return []
        
    except Exception as e:
        logger.error(f"Error getting training documents: {str(e)}")
        return []

async def _monitor_job_progress(job_id: str):
    """Monitor fine-tuning job progress in background"""
    try:
        while True:
            job = await fine_tuning_service.get_fine_tuning_job(job_id)
            
            if job.status in [FineTuningStatus.SUCCEEDED, FineTuningStatus.FAILED, FineTuningStatus.CANCELLED]:
                logger.info(f"Job {job_id} completed with status: {job.status}")
                break
            
            logger.info(f"Job {job_id} status: {job.status}")
            await asyncio.sleep(30)  # Check every 30 seconds
            
    except Exception as e:
        logger.error(f"Error monitoring job {job_id}: {str(e)}")