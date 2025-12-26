"""
Batch Processor Service
REST API for ETL/ELT batch processing and data orchestration
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from etl_pipeline import etl_pipeline, PipelineExecutionRequest, PipelineStatusResponse, PipelineStatus
from src.shared.config.settings import config_manager
from src.shared.storage.sql_service import SQLService
from src.shared.cache.redis_cache import cache_service, cache_result

# Initialize FastAPI app
app = FastAPI(
    title="Batch Processor Service",
    description="ETL/ELT batch processing and data orchestration",
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

# Global variables
config = config_manager.get_azure_config()
sql_service = SQLService(config.sql_connection_string)
logger = logging.getLogger(__name__)

# Pydantic models
class PipelineListResponse(BaseModel):
    pipelines: List[str]
    total_pipelines: int

class ExecutionHistoryResponse(BaseModel):
    executions: List[PipelineStatusResponse]
    total_executions: int
    page: int
    page_size: int

class ScheduleRequest(BaseModel):
    pipeline_name: str
    schedule: str  # Cron expression
    enabled: bool = True

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "batch-processor"
    }

# Pipeline management endpoints
@app.get("/pipelines", response_model=PipelineListResponse)
@cache_result(ttl=300, key_prefix="pipeline_list")  # Cache for 5 minutes
async def list_pipelines():
    """List all available ETL pipelines"""
    try:
        pipelines = list(etl_pipeline.pipelines.keys())
        return PipelineListResponse(
            pipelines=pipelines,
            total_pipelines=len(pipelines)
        )
    except Exception as e:
        logger.error(f"Error listing pipelines: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list pipelines")

@app.get("/pipelines/{pipeline_name}")
async def get_pipeline_details(pipeline_name: str):
    """Get detailed information about a specific pipeline"""
    try:
        if pipeline_name not in etl_pipeline.pipelines:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        steps = etl_pipeline.pipelines[pipeline_name]
        return {
            "pipeline_name": pipeline_name,
            "total_steps": len(steps),
            "steps": [
                {
                    "step_id": step.step_id,
                    "step_name": step.step_name,
                    "transformation_type": step.transformation_type.value,
                    "source_query": step.source_query,
                    "target_table": step.target_table,
                    "dependencies": step.dependencies or [],
                    "enabled": step.enabled
                }
                for step in steps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get pipeline details")

# Pipeline execution endpoints
@app.post("/pipelines/{pipeline_name}/execute")
async def execute_pipeline(
    pipeline_name: str,
    request: PipelineExecutionRequest,
    background_tasks: BackgroundTasks
):
    """Execute an ETL pipeline"""
    try:
        if pipeline_name not in etl_pipeline.pipelines:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Execute pipeline in background
        execution_id = request.execution_id or f"{pipeline_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            etl_pipeline.execute_pipeline,
            pipeline_name,
            execution_id
        )
        
        return {
            "message": f"Pipeline {pipeline_name} execution started",
            "execution_id": execution_id,
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to execute pipeline")

@app.get("/executions/{execution_id}", response_model=PipelineStatusResponse)
async def get_execution_status(execution_id: str):
    """Get the status of a pipeline execution"""
    try:
        if execution_id not in etl_pipeline.executions:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution = etl_pipeline.executions[execution_id]
        
        return PipelineStatusResponse(
            execution_id=execution.execution_id,
            pipeline_name=execution.pipeline_name,
            status=execution.status.value,
            start_time=execution.start_time.isoformat(),
            end_time=execution.end_time.isoformat() if execution.end_time else None,
            records_processed=execution.records_processed,
            records_failed=execution.records_failed,
            error_message=execution.error_message,
            execution_log=execution.execution_log or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get execution status")

@app.get("/executions", response_model=ExecutionHistoryResponse)
@cache_result(ttl=60, key_prefix="execution_history")  # Cache for 1 minute
async def get_execution_history(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None
):
    """Get pipeline execution history"""
    try:
        executions = list(etl_pipeline.executions.values())
        
        # Filter by status if provided
        if status:
            executions = [e for e in executions if e.status.value == status]
        
        # Sort by start time (newest first)
        executions.sort(key=lambda x: x.start_time, reverse=True)
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_executions = executions[start_idx:end_idx]
        
        return ExecutionHistoryResponse(
            executions=[
                PipelineStatusResponse(
                    execution_id=e.execution_id,
                    pipeline_name=e.pipeline_name,
                    status=e.status.value,
                    start_time=e.start_time.isoformat(),
                    end_time=e.end_time.isoformat() if e.end_time else None,
                    records_processed=e.records_processed,
                    records_failed=e.records_failed,
                    error_message=e.error_message,
                    execution_log=e.execution_log or []
                )
                for e in paginated_executions
            ],
            total_executions=len(executions),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting execution history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get execution history")

# Data processing endpoints
@app.post("/process/documents")
async def process_documents_batch(
    background_tasks: BackgroundTasks,
    date_range: Optional[str] = None
):
    """Process documents in batch"""
    try:
        # Execute document processing pipeline
        execution_id = f"document_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            etl_pipeline.execute_pipeline,
            "document_processing",
            execution_id
        )
        
        return {
            "message": "Document batch processing started",
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting document batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start document processing")

@app.post("/process/analytics")
async def process_analytics_batch(
    background_tasks: BackgroundTasks,
    date_range: Optional[str] = None
):
    """Process analytics data in batch"""
    try:
        # Execute analytics processing pipeline
        execution_id = f"analytics_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            etl_pipeline.execute_pipeline,
            "analytics_processing",
            execution_id
        )
        
        return {
            "message": "Analytics batch processing started",
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting analytics batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start analytics processing")

@app.post("/process/users")
async def process_users_batch(
    background_tasks: BackgroundTasks
):
    """Process user analytics in batch"""
    try:
        # Execute user analytics pipeline
        execution_id = f"users_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            etl_pipeline.execute_pipeline,
            "user_analytics",
            execution_id
        )
        
        return {
            "message": "User analytics batch processing started",
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting user analytics processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start user processing")

# Monitoring endpoints
@app.get("/monitoring/dashboard")
@cache_result(ttl=60, key_prefix="batch_dashboard")  # Cache for 1 minute
async def get_batch_dashboard():
    """Get batch processing dashboard data"""
    try:
        executions = list(etl_pipeline.executions.values())
        
        # Calculate statistics
        total_executions = len(executions)
        running_executions = len([e for e in executions if e.status == PipelineStatus.RUNNING])
        completed_executions = len([e for e in executions if e.status == PipelineStatus.COMPLETED])
        failed_executions = len([e for e in executions if e.status == PipelineStatus.FAILED])
        
        # Recent executions (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_executions = [e for e in executions if e.start_time >= recent_cutoff]
        
        # Success rate
        success_rate = (completed_executions / total_executions * 100) if total_executions > 0 else 0
        
        # Average processing time
        completed_with_time = [e for e in executions if e.status == PipelineStatus.COMPLETED and e.end_time]
        avg_processing_time = 0
        if completed_with_time:
            total_time = sum((e.end_time - e.start_time).total_seconds() for e in completed_with_time)
            avg_processing_time = total_time / len(completed_with_time)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_executions": total_executions,
                "running_executions": running_executions,
                "completed_executions": completed_executions,
                "failed_executions": failed_executions,
                "success_rate": round(success_rate, 2),
                "avg_processing_time_seconds": round(avg_processing_time, 2)
            },
            "recent_activity": {
                "last_24h_executions": len(recent_executions),
                "last_execution": max(executions, key=lambda x: x.start_time).start_time.isoformat() if executions else None
            },
            "pipelines": {
                "available_pipelines": len(etl_pipeline.pipelines),
                "pipeline_names": list(etl_pipeline.pipelines.keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting batch dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get batch dashboard")

@app.get("/monitoring/health")
async def get_batch_health():
    """Get batch processing system health"""
    try:
        # Check if any pipelines are stuck (running for more than 1 hour)
        stuck_executions = []
        for execution in etl_pipeline.executions.values():
            if execution.status == PipelineStatus.RUNNING:
                if datetime.utcnow() - execution.start_time > timedelta(hours=1):
                    stuck_executions.append(execution.execution_id)
        
        # Check recent failure rate
        recent_executions = [e for e in etl_pipeline.executions.values() 
                           if e.start_time >= datetime.utcnow() - timedelta(hours=1)]
        recent_failures = len([e for e in recent_executions if e.status == PipelineStatus.FAILED])
        failure_rate = (recent_failures / len(recent_executions) * 100) if recent_executions else 0
        
        health_status = "healthy"
        if stuck_executions:
            health_status = "warning"
        if failure_rate > 50:
            health_status = "critical"
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": {
                "stuck_executions": len(stuck_executions),
                "recent_failure_rate": round(failure_rate, 2),
                "stuck_execution_ids": stuck_executions
            },
            "recommendations": _get_health_recommendations(stuck_executions, failure_rate)
        }
        
    except Exception as e:
        logger.error(f"Error getting batch health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get batch health")

def _get_health_recommendations(stuck_executions: List[str], failure_rate: float) -> List[str]:
    """Get health recommendations based on system status"""
    recommendations = []
    
    if stuck_executions:
        recommendations.append(f"Investigate {len(stuck_executions)} stuck executions")
    
    if failure_rate > 50:
        recommendations.append("High failure rate detected - check pipeline configurations")
    elif failure_rate > 20:
        recommendations.append("Moderate failure rate - monitor pipeline executions")
    
    if not recommendations:
        recommendations.append("System is healthy - no issues detected")
    
    return recommendations

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)