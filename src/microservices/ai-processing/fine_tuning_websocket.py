"""
Fine-Tuning WebSocket Endpoints
Real-time WebSocket connections for fine-tuning dashboard
"""

import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from .fine_tuning_dashboard import FineTuningDashboard

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize dashboard
dashboard = FineTuningDashboard()

@router.websocket("/ws/fine-tuning-dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for fine-tuning dashboard"""
    await dashboard.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            await dashboard.handle_websocket_message(websocket, data)
            
    except WebSocketDisconnect:
        dashboard.disconnect(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        dashboard.disconnect(websocket)

@router.websocket("/ws/fine-tuning-job/{job_id}")
async def websocket_job_monitor(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for monitoring specific job"""
    await websocket.accept()
    
    try:
        # Start monitoring the specific job
        await dashboard._monitor_job_updates(websocket, job_id)
        
    except WebSocketDisconnect:
        logger.info(f"Job monitoring WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"Job monitoring WebSocket error: {str(e)}")

@router.websocket("/ws/fine-tuning-workflow/{workflow_id}")
async def websocket_workflow_monitor(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for monitoring specific workflow"""
    await websocket.accept()
    
    try:
        # Start monitoring the specific workflow
        await dashboard._monitor_workflow_updates(websocket, workflow_id)
        
    except WebSocketDisconnect:
        logger.info(f"Workflow monitoring WebSocket disconnected for workflow {workflow_id}")
    except Exception as e:
        logger.error(f"Workflow monitoring WebSocket error: {str(e)}")