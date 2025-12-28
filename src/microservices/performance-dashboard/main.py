"""
Performance Dashboard Microservice
Real-time performance monitoring and optimization dashboard
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.shared.monitoring.performance_monitor import performance_monitor
from src.shared.cache.redis_cache import cache_service

# Initialize FastAPI app
app = FastAPI(
    title="Performance Dashboard",
    description="Real-time performance monitoring and optimization dashboard",
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
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, ConnectionClosedError, RuntimeError) as e:
                # Remove broken connections
                self.active_connections.remove(connection)
                self.logger.warning(f"Removed broken WebSocket connection: {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error sending message: {str(e)}")

manager = ConnectionManager()

# Pydantic models
class PerformanceAlert(BaseModel):
    alert_type: str
    message: str
    severity: str
    timestamp: datetime
    service: str

class OptimizationRecommendation(BaseModel):
    category: str
    title: str
    description: str
    impact: str
    effort: str
    priority: int

# Performance dashboard HTML
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Get performance dashboard HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Performance Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric { display: flex; justify-content: space-between; margin: 10px 0; }
            .metric-value { font-weight: bold; color: #2c3e50; }
            .status-healthy { color: #27ae60; }
            .status-warning { color: #f39c12; }
            .status-critical { color: #e74c3c; }
            .chart { height: 200px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
            .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
            .alert-critical { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .alert-warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
            .alert-info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
            .optimization { background: #e8f5e8; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; }
            .optimization h4 { margin: 0 0 10px 0; color: #155724; }
            .optimization p { margin: 5px 0; color: #155724; }
            .priority-high { border-left-color: #dc3545; }
            .priority-medium { border-left-color: #ffc107; }
            .priority-low { border-left-color: #28a745; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1> Performance Dashboard</h1>
                <p>Real-time system performance monitoring and optimization</p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3> System Metrics</h3>
                    <div id="system-metrics">
                        <div class="metric">
                            <span>CPU Usage:</span>
                            <span class="metric-value" id="cpu-usage">Loading...</span>
                        </div>
                        <div class="metric">
                            <span>Memory Usage:</span>
                            <span class="metric-value" id="memory-usage">Loading...</span>
                        </div>
                        <div class="metric">
                            <span>Disk Usage:</span>
                            <span class="metric-value" id="disk-usage">Loading...</span>
                        </div>
                        <div class="metric">
                            <span>Active Processes:</span>
                            <span class="metric-value" id="process-count">Loading...</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3> Performance Summary</h3>
                    <div id="performance-summary">
                        <div class="metric">
                            <span>Functions Called:</span>
                            <span class="metric-value" id="functions-called">Loading...</span>
                        </div>
                        <div class="metric">
                            <span>Total Calls:</span>
                            <span class="metric-value" id="total-calls">Loading...</span>
                        </div>
                        <div class="metric">
                            <span>Avg Response Time:</span>
                            <span class="metric-value" id="avg-response-time">Loading...</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3> Active Alerts</h3>
                    <div id="alerts-container">
                        <div class="alert alert-info">No active alerts</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3> Optimization Recommendations</h3>
                    <div id="optimizations-container">
                        <div class="optimization priority-high">
                            <h4>High Priority: Enable Connection Pooling</h4>
                            <p>Database connections are not pooled, causing 3-5x slower performance</p>
                            <p><strong>Impact:</strong> 3-5x faster database operations</p>
                        </div>
                        <div class="optimization priority-medium">
                            <h4>Medium Priority: Implement Caching</h4>
                            <p>API responses are not cached, causing repeated database queries</p>
                            <p><strong>Impact:</strong> 2-3x faster API responses</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket("ws://localhost:8004/ws");
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            function updateDashboard(data) {
                if (data.system_metrics) {
                    document.getElementById('cpu-usage').textContent = data.system_metrics.cpu.usage_percent + '%';
                    document.getElementById('memory-usage').textContent = data.system_metrics.memory.usage_percent + '%';
                    document.getElementById('disk-usage').textContent = data.system_metrics.disk.usage_percent + '%';
                    document.getElementById('process-count').textContent = data.system_metrics.processes.count;
                }
                
                if (data.performance_summary) {
                    document.getElementById('functions-called').textContent = data.performance_summary.total_functions_called;
                    document.getElementById('total-calls').textContent = data.performance_summary.total_calls;
                }
            }
            
            // Auto-refresh every 5 seconds
            setInterval(() => {
                fetch('/api/system-metrics')
                    .then(response => response.json())
                    .then(data => updateDashboard(data));
            }, 5000);
        </script>
    </body>
    </html>
    """

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send performance data every 5 seconds
            system_metrics = await performance_monitor.get_system_metrics()
            performance_summary = await performance_monitor.get_performance_summary()
            
            data = {
                "system_metrics": system_metrics,
                "performance_summary": performance_summary,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.send_personal_message(
                f"data: {json.dumps(data)}",
                websocket
            )
            
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# API endpoints
@app.get("/api/system-metrics")
async def get_system_metrics():
    """Get current system metrics"""
    try:
        metrics = await performance_monitor.get_system_metrics()
        return {"system_metrics": metrics}
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")

@app.get("/api/performance-summary")
async def get_performance_summary():
    """Get performance summary"""
    try:
        summary = await performance_monitor.get_performance_summary()
        return {"performance_summary": summary}
    except Exception as e:
        logger.error(f"Error getting performance summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get performance summary")

@app.post("/api/optimize-memory")
async def optimize_memory():
    """Optimize memory usage"""
    try:
        result = await performance_monitor.optimize_memory()
        return {"optimization_result": result}
    except Exception as e:
        logger.error(f"Error optimizing memory: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to optimize memory")

@app.get("/api/cache-stats")
async def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = await cache_service.get_stats()
        return {"cache_stats": stats}
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "performance-dashboard"
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint (legacy)"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "performance-dashboard"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)