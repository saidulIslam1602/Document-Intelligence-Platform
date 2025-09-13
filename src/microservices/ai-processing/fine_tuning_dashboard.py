"""
Fine-Tuning Dashboard
WebSocket-based real-time dashboard for monitoring fine-tuning progress
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from .fine_tuning_service import DocumentFineTuningService, FineTuningStatus
from .fine_tuning_workflow import DocumentFineTuningWorkflow, WorkflowStatus
from ...shared.events.event_sourcing import EventBus

class FineTuningDashboard:
    """Real-time fine-tuning dashboard"""
    
    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.fine_tuning_service = DocumentFineTuningService(event_bus)
        self.workflow_service = DocumentFineTuningWorkflow(event_bus)
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Dashboard data cache
        self.dashboard_data = {
            "active_jobs": [],
            "completed_jobs": [],
            "workflows": [],
            "metrics": {
                "total_jobs": 0,
                "successful_jobs": 0,
                "failed_jobs": 0,
                "average_training_time": 0,
                "total_cost": 0.0
            }
        }
    
    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial dashboard data
        await self.send_dashboard_data(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_dashboard_data(self, websocket: WebSocket):
        """Send current dashboard data to WebSocket"""
        try:
            # Update dashboard data
            await self._update_dashboard_data()
            
            # Send data
            await websocket.send_text(json.dumps({
                "type": "dashboard_data",
                "data": self.dashboard_data,
                "timestamp": datetime.now().isoformat()
            }))
            
        except Exception as e:
            self.logger.error(f"Error sending dashboard data: {str(e)}")
    
    async def broadcast_update(self, update_type: str, data: Dict[str, Any]):
        """Broadcast update to all connected clients"""
        if not self.active_connections:
            return
        
        message = json.dumps({
            "type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send to all connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, ConnectionClosedError, RuntimeError) as e:
                disconnected.append(connection)
                self.logger.warning(f"Removed broken WebSocket connection: {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error sending message: {str(e)}")
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def handle_websocket_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "get_job_status":
                job_id = data.get("job_id")
                await self._handle_job_status_request(websocket, job_id)
            
            elif message_type == "get_workflow_status":
                workflow_id = data.get("workflow_id")
                await self._handle_workflow_status_request(websocket, workflow_id)
            
            elif message_type == "get_metrics":
                await self._handle_metrics_request(websocket)
            
            elif message_type == "subscribe_job":
                job_id = data.get("job_id")
                await self._handle_job_subscription(websocket, job_id)
            
            elif message_type == "subscribe_workflow":
                workflow_id = data.get("workflow_id")
                await self._handle_workflow_subscription(websocket, workflow_id)
            
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
                
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _update_dashboard_data(self):
        """Update dashboard data from services"""
        try:
            # Get active jobs
            active_jobs = []
            all_jobs = await self.fine_tuning_service.list_fine_tuning_jobs(limit=50)
            
            for job in all_jobs:
                job_data = {
                    "job_id": job.job_id,
                    "model_name": job.model_name,
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat(),
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                    "training_tokens": job.training_tokens,
                    "error_message": job.error_message
                }
                
                if job.status in [FineTuningStatus.PENDING, FineTuningStatus.RUNNING]:
                    active_jobs.append(job_data)
                else:
                    self.dashboard_data["completed_jobs"].append(job_data)
            
            self.dashboard_data["active_jobs"] = active_jobs
            
            # Calculate metrics
            total_jobs = len(all_jobs)
            successful_jobs = len([j for j in all_jobs if j.status == FineTuningStatus.SUCCEEDED])
            failed_jobs = len([j for j in all_jobs if j.status == FineTuningStatus.FAILED])
            
            self.dashboard_data["metrics"] = {
                "total_jobs": total_jobs,
                "successful_jobs": successful_jobs,
                "failed_jobs": failed_jobs,
                "success_rate": successful_jobs / total_jobs if total_jobs > 0 else 0,
                "average_training_time": await self._calculate_average_training_time(all_jobs),
                "total_cost": await self._calculate_total_cost(all_jobs)
            }
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard data: {str(e)}")
    
    async def _handle_job_status_request(self, websocket: WebSocket, job_id: str):
        """Handle job status request"""
        try:
            if not job_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Job ID required"
                }))
                return
            
            job = await self.fine_tuning_service.get_fine_tuning_job(job_id)
            
            job_data = {
                "job_id": job.job_id,
                "model_name": job.model_name,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "training_tokens": job.training_tokens,
                "hyperparameters": job.hyperparameters,
                "error_message": job.error_message
            }
            
            await websocket.send_text(json.dumps({
                "type": "job_status",
                "data": job_data
            }))
            
        except Exception as e:
            self.logger.error(f"Error handling job status request: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _handle_workflow_status_request(self, websocket: WebSocket, workflow_id: str):
        """Handle workflow status request"""
        try:
            if not workflow_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Workflow ID required"
                }))
                return
            
            workflow = await self.workflow_service._get_workflow(workflow_id)
            
            if not workflow:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Workflow not found"
                }))
                return
            
            workflow_data = {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "status": workflow.status.value,
                "model_name": workflow.model_name,
                "document_type": workflow.document_type,
                "industry": workflow.industry,
                "created_at": workflow.created_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat(),
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "name": step.name,
                        "status": step.status,
                        "started_at": step.started_at.isoformat() if step.started_at else None,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                        "error_message": step.error_message,
                        "metrics": step.metrics
                    }
                    for step in workflow.steps
                ],
                "metrics": workflow.metrics
            }
            
            await websocket.send_text(json.dumps({
                "type": "workflow_status",
                "data": workflow_data
            }))
            
        except Exception as e:
            self.logger.error(f"Error handling workflow status request: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _handle_metrics_request(self, websocket: WebSocket):
        """Handle metrics request"""
        try:
            await self._update_dashboard_data()
            
            await websocket.send_text(json.dumps({
                "type": "metrics",
                "data": self.dashboard_data["metrics"]
            }))
            
        except Exception as e:
            self.logger.error(f"Error handling metrics request: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _handle_job_subscription(self, websocket: WebSocket, job_id: str):
        """Handle job subscription for real-time updates"""
        try:
            if not job_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Job ID required for subscription"
                }))
                return
            
            # Start monitoring job
            asyncio.create_task(self._monitor_job_updates(websocket, job_id))
            
            await websocket.send_text(json.dumps({
                "type": "subscription_started",
                "message": f"Started monitoring job {job_id}"
            }))
            
        except Exception as e:
            self.logger.error(f"Error handling job subscription: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _handle_workflow_subscription(self, websocket: WebSocket, workflow_id: str):
        """Handle workflow subscription for real-time updates"""
        try:
            if not workflow_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Workflow ID required for subscription"
                }))
                return
            
            # Start monitoring workflow
            asyncio.create_task(self._monitor_workflow_updates(websocket, workflow_id))
            
            await websocket.send_text(json.dumps({
                "type": "subscription_started",
                "message": f"Started monitoring workflow {workflow_id}"
            }))
            
        except Exception as e:
            self.logger.error(f"Error handling workflow subscription: {str(e)}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _monitor_job_updates(self, websocket: WebSocket, job_id: str):
        """Monitor job for updates"""
        try:
            last_status = None
            
            while websocket in self.active_connections:
                try:
                    job = await self.fine_tuning_service.get_fine_tuning_job(job_id)
                    
                    if job.status != last_status:
                        await websocket.send_text(json.dumps({
                            "type": "job_update",
                            "data": {
                                "job_id": job.job_id,
                                "status": job.status.value,
                                "updated_at": datetime.now().isoformat(),
                                "training_tokens": job.training_tokens,
                                "error_message": job.error_message
                            }
                        }))
                        
                        last_status = job.status
                        
                        # Stop monitoring if job is complete
                        if job.status in [FineTuningStatus.SUCCEEDED, FineTuningStatus.FAILED, FineTuningStatus.CANCELLED]:
                            break
                    
                    await asyncio.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error monitoring job {job_id}: {str(e)}")
                    break
            
        except Exception as e:
            self.logger.error(f"Error in job monitoring: {str(e)}")
    
    async def _monitor_workflow_updates(self, websocket: WebSocket, workflow_id: str):
        """Monitor workflow for updates"""
        try:
            last_status = None
            
            while websocket in self.active_connections:
                try:
                    workflow = await self.workflow_service._get_workflow(workflow_id)
                    
                    if not workflow:
                        break
                    
                    if workflow.status != last_status:
                        await websocket.send_text(json.dumps({
                            "type": "workflow_update",
                            "data": {
                                "workflow_id": workflow.workflow_id,
                                "status": workflow.status.value,
                                "updated_at": workflow.updated_at.isoformat(),
                                "current_step": self._get_current_step(workflow),
                                "progress": self._calculate_progress(workflow)
                            }
                        }))
                        
                        last_status = workflow.status
                        
                        # Stop monitoring if workflow is complete
                        if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
                            break
                    
                    await asyncio.sleep(15)  # Check every 15 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error monitoring workflow {workflow_id}: {str(e)}")
                    break
            
        except Exception as e:
            self.logger.error(f"Error in workflow monitoring: {str(e)}")
    
    def _get_current_step(self, workflow) -> Optional[str]:
        """Get current workflow step"""
        for step in workflow.steps:
            if step.status == "running":
                return step.step_id
        return None
    
    def _calculate_progress(self, workflow) -> float:
        """Calculate workflow progress percentage"""
        completed_steps = len([s for s in workflow.steps if s.status == "completed"])
        total_steps = len(workflow.steps)
        return (completed_steps / total_steps) * 100 if total_steps > 0 else 0
    
    async def _calculate_average_training_time(self, jobs: List) -> float:
        """Calculate average training time in hours"""
        try:
            completed_jobs = [
                j for j in jobs 
                if j.status == FineTuningStatus.SUCCEEDED and j.finished_at and j.created_at
            ]
            
            if not completed_jobs:
                return 0.0
            
            total_time = 0.0
            for job in completed_jobs:
                duration = (job.finished_at - job.created_at).total_seconds() / 3600
                total_time += duration
            
            return total_time / len(completed_jobs)
            
        except Exception as e:
            self.logger.error(f"Error calculating average training time: {str(e)}")
            return 0.0
    
    async def _calculate_total_cost(self, jobs: List) -> float:
        """Calculate total cost of all jobs"""
        try:
            total_cost = 0.0
            
            for job in jobs:
                if job.training_tokens:
                    model_info = self.fine_tuning_service.supported_models.get(job.model_name, {})
                    training_cost = (job.training_tokens / 1000) * model_info.get("training_cost_per_1k_tokens", 0)
                    total_cost += training_cost
                    
                    # Add hosting cost (estimate 2 hours per job)
                    hosting_cost = model_info.get("hosting_cost_per_hour", 0) * 2
                    total_cost += hosting_cost
            
            return total_cost
            
        except Exception as e:
            self.logger.error(f"Error calculating total cost: {str(e)}")
            return 0.0

# HTML Dashboard Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Fine-Tuning Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #f5f5f5; padding: 20px; border-radius: 8px; }
        .status { padding: 4px 8px; border-radius: 4px; color: white; }
        .status.pending { background: #ffc107; }
        .status.running { background: #17a2b8; }
        .status.succeeded { background: #28a745; }
        .status.failed { background: #dc3545; }
        .metrics { display: flex; justify-content: space-between; }
        .metric { text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { font-size: 12px; color: #666; }
        #chart { width: 100%; height: 300px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Fine-Tuning Dashboard</h1>
        
        <div class="grid">
            <div class="card">
                <h3>Active Jobs</h3>
                <div id="active-jobs"></div>
            </div>
            
            <div class="card">
                <h3>Metrics</h3>
                <div class="metrics" id="metrics"></div>
            </div>
            
            <div class="card">
                <h3>Training Progress</h3>
                <canvas id="chart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const ws = new WebSocket("ws://localhost:8000/ws/fine-tuning-dashboard");
        let chart;

        ws.onopen = function(event) {
            console.log("Connected to dashboard");
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("Received:", data);
            
            if (data.type === "dashboard_data") {
                updateDashboard(data.data);
            } else if (data.type === "job_update") {
                updateJobStatus(data.data);
            } else if (data.type === "workflow_update") {
                updateWorkflowStatus(data.data);
            }
        };

        ws.onclose = function(event) {
            console.log("Disconnected from dashboard");
        };

        function updateDashboard(data) {
            updateActiveJobs(data.active_jobs);
            updateMetrics(data.metrics);
            updateChart(data.completed_jobs);
        }

        function updateActiveJobs(jobs) {
            const container = document.getElementById('active-jobs');
            container.innerHTML = '';
            
            jobs.forEach(job => {
                const div = document.createElement('div');
                div.innerHTML = `
                    <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 4px;">
                        <strong>${job.job_id}</strong>
                        <span class="status ${job.status}">${job.status}</span>
                        <br>
                        <small>Model: ${job.model_name}</small>
                        <br>
                        <small>Created: ${new Date(job.created_at).toLocaleString()}</small>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function updateMetrics(metrics) {
            const container = document.getElementById('metrics');
            container.innerHTML = `
                <div class="metric">
                    <div class="metric-value">${metrics.total_jobs}</div>
                    <div class="metric-label">Total Jobs</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${metrics.successful_jobs}</div>
                    <div class="metric-label">Successful</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${metrics.failed_jobs}</div>
                    <div class="metric-label">Failed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${(metrics.success_rate * 100).toFixed(1)}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            `;
        }

        function updateChart(jobs) {
            const ctx = document.getElementById('chart').getContext('2d');
            
            if (chart) {
                chart.destroy();
            }
            
            const statusCounts = jobs.reduce((acc, job) => {
                acc[job.status] = (acc[job.status] || 0) + 1;
                return acc;
            }, {});
            
            chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statusCounts),
                    datasets: [{
                        data: Object.values(statusCounts),
                        backgroundColor: ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        function updateJobStatus(job) {
            console.log("Job update:", job);
            // Update specific job in the UI
        }

        function updateWorkflowStatus(workflow) {
            console.log("Workflow update:", workflow);
            // Update specific workflow in the UI
        }
    </script>
</body>
</html>
"""

def get_dashboard_html():
    """Get dashboard HTML"""
    return HTMLResponse(content=DASHBOARD_HTML)