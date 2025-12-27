"""
Microsoft 365 Integration Microservice
FastAPI endpoints for M365 document processing and Copilot integration
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from copilot_service import M365CopilotService
from src.shared.config.settings import config_manager
from src.shared.events.event_sourcing import EventBus

# Initialize FastAPI app
app = FastAPI(
    title="M365 Integration Service",
    description="Microsoft 365 document integration and Copilot functionality",
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
logger = logging.getLogger(__name__)

# Initialize services
event_bus = EventBus()
m365_service = M365CopilotService(event_bus=event_bus)

# Pydantic models
class M365DocumentRequest(BaseModel):
    document_id: str = Field(..., description="M365 document ID")
    service: str = Field(..., description="M365 service (sharepoint, onedrive, teams)")
    user_id: str
    
class CopilotSuggestionRequest(BaseModel):
    context: str = Field(..., description="Context for generating suggestions")
    user_id: str
    service: str = "general"

class TeamAnalysisRequest(BaseModel):
    team_id: str = Field(..., description="Microsoft Teams team ID")

class WorkflowOptimizationRequest(BaseModel):
    user_id: str = Field(..., description="User ID to optimize workflow for")

class M365SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    user_id: str
    service: str = Field("sharepoint", description="Service to search in")
    limit: int = Field(20, description="Number of results to return")

# Dependency injection
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)) -> str:
    """Extract user ID from JWT token - Development mode: No auth required"""
    if credentials is None:
        return "dev_user"
    return "user_123"

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "m365-integration",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# M365 Document Processing Endpoints
@app.post("/m365/documents/process")
async def process_m365_document(
    request: M365DocumentRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Process a document from Microsoft 365 (SharePoint, OneDrive, Teams)
    
    Extracts document from M365 service and applies AI-powered processing
    """
    try:
        result = await m365_service.process_m365_document(
            document_id=request.document_id,
            user_id=request.user_id,
            service=request.service
        )
        
        logger.info(f"Processed M365 document {request.document_id} from {request.service}")
        
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing M365 document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/m365/copilot/suggestions")
async def get_copilot_suggestions(
    request: CopilotSuggestionRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Generate Copilot-like AI suggestions based on context
    
    Provides intelligent recommendations similar to M365 Copilot
    """
    try:
        suggestions = await m365_service.generate_copilot_suggestions(
            context=request.context,
            user_id=request.user_id,
            service=request.service
        )
        
        logger.info(f"Generated {len(suggestions)} Copilot suggestions for user {request.user_id}")
        
        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating Copilot suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")

@app.post("/m365/teams/analyze")
async def analyze_team_collaboration(
    request: TeamAnalysisRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Analyze team collaboration patterns using Microsoft Teams data
    
    Provides insights into communication and document collaboration
    """
    try:
        analysis = await m365_service.analyze_team_collaboration(
            team_id=request.team_id
        )
        
        logger.info(f"Analyzed collaboration for team {request.team_id}")
        
        return {
            "success": True,
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing team collaboration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/m365/workflow/optimize")
async def optimize_workflow(
    request: WorkflowOptimizationRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Optimize workflow efficiency using M365 data and AI
    
    Identifies bottlenecks and provides recommendations
    """
    try:
        optimization = await m365_service.optimize_workflow_efficiency(
            user_id=request.user_id
        )
        
        logger.info(f"Optimized workflow for user {request.user_id}")
        
        return {
            "success": True,
            "optimization": optimization,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/m365/documents/list")
async def list_m365_documents(
    service: str = Query("sharepoint", description="M365 service"),
    user_id: str = Depends(get_current_user),
    limit: int = Query(20, description="Number of documents to return")
):
    """
    List documents from M365 service (SharePoint, OneDrive, Teams)
    """
    try:
        # This would call the M365 service to list documents
        return {
            "success": True,
            "service": service,
            "documents": [],  # Placeholder - implement actual listing
            "count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing M365 documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Listing failed: {str(e)}")

@app.post("/m365/documents/search")
async def search_m365_documents(
    request: M365SearchRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Search documents in M365 services
    
    Supports searching across SharePoint, OneDrive, and Teams
    """
    try:
        # This would call the M365 service to search documents
        return {
            "success": True,
            "query": request.query,
            "service": request.service,
            "results": [],  # Placeholder - implement actual search
            "count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error searching M365 documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/m365/documents/{document_id}/metadata")
async def get_document_metadata(
    document_id: str,
    service: str = Query("sharepoint", description="M365 service"),
    user_id: str = Depends(get_current_user)
):
    """
    Get metadata for an M365 document
    """
    try:
        # This would call the M365 service to get metadata
        return {
            "success": True,
            "document_id": document_id,
            "service": service,
            "metadata": {},  # Placeholder - implement actual metadata retrieval
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting document metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metadata retrieval failed: {str(e)}")

@app.get("/m365/sync/status")
async def get_sync_status(user_id: str = Depends(get_current_user)):
    """
    Get M365 synchronization status
    """
    try:
        return {
            "success": True,
            "user_id": user_id,
            "sync_status": {
                "sharepoint": "active",
                "onedrive": "active",
                "teams": "active",
                "outlook": "inactive"
            },
            "last_sync": datetime.utcnow().isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("M365 Integration Service started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("M365 Integration Service shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)

