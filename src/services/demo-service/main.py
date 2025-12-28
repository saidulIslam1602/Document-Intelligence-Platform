"""
Demo Service API
Main API for customer demonstrations and PoC management
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from src.shared.config.settings import config_manager
from src.shared.auth.auth_service import auth_service, User

try:
    from poc_generator import PoCGenerator, PoCInstance, PoCScenario
except ImportError:
    # Stub classes for when poc_generator is not available
    class PoCGenerator:
        pass
    class PoCInstance:
        pass
    class PoCScenario:
        pass

# Initialize FastAPI app
app = FastAPI(
    title="Demo Service",
    description="Customer demonstration and PoC management service",
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
logger = logging.getLogger(__name__)

# Demo services
poc_generator = PoCGenerator()

# Pydantic models
class PoCCreateRequest(BaseModel):
    scenario_id: str = Field(..., description="PoC scenario ID")
    customer_name: str = Field(..., description="Customer name")
    customer_email: str = Field(..., description="Customer email")

class PoCStepRequest(BaseModel):
    instance_id: str = Field(..., description="PoC instance ID")
    step_number: int = Field(..., description="Step number to execute")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    user = auth_service.validate_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "demo-service"}

@app.get("/scenarios")
async def list_scenarios(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """List all available PoC scenarios"""
    try:
        scenarios = await poc_generator.list_available_scenarios()
        return scenarios
    except Exception as e:
        logger.error(f"Error listing scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list scenarios: {str(e)}")

@app.post("/poc/create")
async def create_poc(
    request: PoCCreateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new PoC instance"""
    try:
        instance = await poc_generator.create_poc_instance(
            request.scenario_id,
            request.customer_name,
            request.customer_email
        )
        
        return {
            "instance_id": instance.instance_id,
            "scenario_id": instance.scenario_id,
            "customer_name": instance.customer_name,
            "status": instance.status.value,
            "created_at": instance.created_at.isoformat(),
            "total_steps": instance.total_steps
        }
    except Exception as e:
        logger.error(f"Error creating PoC: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create PoC: {str(e)}")

@app.post("/poc/{instance_id}/start")
async def start_poc(
    instance_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start a PoC instance"""
    try:
        result = await poc_generator.start_poc(instance_id)
        return result
    except Exception as e:
        logger.error(f"Error starting PoC: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start PoC: {str(e)}")

@app.post("/poc/step")
async def execute_poc_step(
    request: PoCStepRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Execute a PoC step"""
    try:
        result = await poc_generator.execute_poc_step(
            request.instance_id,
            request.step_number
        )
        return result
    except Exception as e:
        logger.error(f"Error executing PoC step: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to execute PoC step: {str(e)}")

@app.get("/poc/{instance_id}/progress")
async def get_poc_progress(
    instance_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get PoC progress"""
    try:
        progress = await poc_generator.get_poc_progress(instance_id)
        return progress
    except Exception as e:
        logger.error(f"Error getting PoC progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get PoC progress: {str(e)}")

@app.get("/poc/{instance_id}/report")
async def generate_poc_report(
    instance_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate PoC report"""
    try:
        report = await poc_generator.generate_poc_report(instance_id)
        return report
    except Exception as e:
        logger.error(f"Error generating PoC report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PoC report: {str(e)}")

@app.get("/demo/quick-setup")
async def quick_demo_setup(
    demo_type: str = "document_intelligence",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Quick setup for customer demonstrations"""
    try:
        # This would set up a quick demo environment
        demo_config = {
            "demo_type": demo_type,
            "status": "ready",
            "endpoints": {
                "document_upload": "http://localhost:8000/upload",
                "ai_processing": "http://localhost:8001/process",
                "analytics": "http://localhost:8002/analytics",
                "ai_chat": "http://localhost:8003/chat"
            },
            "sample_data": {
                "documents": [
                    "sample_invoice.pdf",
                    "sample_contract.docx",
                    "sample_report.xlsx"
                ],
                "queries": [
                    "What is the total amount in the invoice?",
                    "Summarize the contract terms",
                    "What are the key metrics in the report?"
                ]
            },
            "demo_script": [
                "1. Upload sample documents",
                "2. Process with AI services",
                "3. View extracted data",
                "4. Ask questions via AI chat",
                "5. Review analytics dashboard"
            ]
        }
        
        return demo_config
    except Exception as e:
        logger.error(f"Error setting up quick demo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to setup demo: {str(e)}")

@app.get("/demo/workshop-materials")
async def get_workshop_materials(
    workshop_type: str = "architecture",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get workshop materials and resources"""
    try:
        materials = {
            "workshop_type": workshop_type,
            "presentation_slides": f"https://example.com/slides/{workshop_type}.pptx",
            "hands_on_lab": f"https://example.com/labs/{workshop_type}_lab.md",
            "sample_code": f"https://example.com/code/{workshop_type}_samples.zip",
            "architecture_diagrams": [
                "https://example.com/diagrams/overview.png",
                "https://example.com/diagrams/data_flow.png",
                "https://example.com/diagrams/security.png"
            ],
            "best_practices": f"https://example.com/docs/{workshop_type}_best_practices.md",
            "troubleshooting_guide": f"https://example.com/docs/{workshop_type}_troubleshooting.md"
        }
        
        return materials
    except Exception as e:
        logger.error(f"Error getting workshop materials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workshop materials: {str(e)}")

@app.post("/demo/roi-calculator")
async def calculate_roi(
    current_system_cost: float,
    current_processing_time_hours: float,
    document_volume_per_month: int,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Calculate ROI for migration to the platform"""
    try:
        # Calculate current costs
        current_monthly_cost = current_system_cost
        current_processing_cost = current_processing_time_hours * 50  # $50/hour
        
        # Calculate new platform costs
        new_platform_cost = document_volume_per_month * 0.10  # $0.10 per document
        new_processing_cost = document_volume_per_month * 0.05  # $0.05 per document processing
        
        total_new_cost = new_platform_cost + new_processing_cost
        
        # Calculate savings
        monthly_savings = current_monthly_cost - total_new_cost
        annual_savings = monthly_savings * 12
        
        # Calculate ROI
        roi_percentage = (annual_savings / current_monthly_cost) * 100 if current_monthly_cost > 0 else 0
        
        # Calculate payback period
        payback_months = current_monthly_cost / monthly_savings if monthly_savings > 0 else 0
        
        return {
            "current_system": {
                "monthly_cost": current_monthly_cost,
                "processing_cost": current_processing_cost,
                "total_monthly_cost": current_monthly_cost + current_processing_cost
            },
            "new_platform": {
                "platform_cost": new_platform_cost,
                "processing_cost": new_processing_cost,
                "total_monthly_cost": total_new_cost
            },
            "savings": {
                "monthly_savings": monthly_savings,
                "annual_savings": annual_savings,
                "roi_percentage": roi_percentage,
                "payback_months": payback_months
            },
            "recommendations": [
                f"Potential annual savings: ${annual_savings:,.2f}",
                f"ROI: {roi_percentage:.1f}%",
                f"Payback period: {payback_months:.1f} months",
                "Consider migration for cost optimization"
            ]
        }
    except Exception as e:
        logger.error(f"Error calculating ROI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate ROI: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)