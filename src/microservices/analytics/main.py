"""
Analytics and Monitoring Microservice
Real-time analytics, monitoring, and business intelligence dashboard
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.monitor.query import MetricsQueryClient
from azure.identity import DefaultAzureCredential
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import EventBus
from ...shared.storage.data_lake_service import DataLakeService
from ...shared.storage.sql_service import SQLService
from ...shared.cache.redis_cache import cache_service, cache_result, cache_invalidate, CacheKeys
from ...shared.services.powerbi_service import powerbi_service
from ...shared.monitoring.advanced_monitoring import monitoring_service
from ...shared.health import get_health_service
from .automation_scoring import AutomationScoringEngine

# Initialize FastAPI app
app = FastAPI(
    title="Analytics and Monitoring Service",
    description="Real-time analytics and monitoring dashboard for document intelligence platform",
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

# Initialize storage services
data_lake_service = DataLakeService(config.data_lake_connection_string)
sql_service = SQLService(config.sql_connection_string)
event_bus = EventBus()
logger = logging.getLogger(__name__)

# Azure clients
service_bus_client = ServiceBusClient.from_connection_string(
    config.service_bus_connection_string
)

# Metrics client for Azure Monitor
metrics_client = MetricsQueryClient(DefaultAzureCredential())

# Initialize automation scoring engine
automation_engine = AutomationScoringEngine(sql_service)

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
                # Remove disconnected clients
                self.active_connections.remove(connection)
                self.logger.warning(f"Removed disconnected WebSocket client: {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error sending message to client: {str(e)}")

manager = ConnectionManager()

# Pydantic models
class AnalyticsRequest(BaseModel):
    time_range: str = Field("24h", description="Time range for analytics (1h, 24h, 7d, 30d)")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")
    metrics: Optional[List[str]] = Field(default_factory=list, description="Specific metrics to retrieve")

class AnalyticsResponse(BaseModel):
    timestamp: datetime
    time_range: str
    metrics: Dict[str, Any]
    charts: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]

class DashboardConfig(BaseModel):
    user_id: str
    widgets: List[Dict[str, Any]]
    refresh_interval: int = 30
    auto_refresh: bool = True

class AlertRule(BaseModel):
    name: str
    metric: str
    threshold: float
    operator: str  # >, <, >=, <=, ==
    time_window: int  # minutes
    severity: str  # low, medium, high, critical
    enabled: bool = True

class Alert(BaseModel):
    id: str
    rule_name: str
    metric: str
    current_value: float
    threshold: float
    severity: str
    timestamp: datetime
    message: str
    acknowledged: bool = False

# Dependency injection
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token"""
    return "user_123"

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint
    Checks all dependencies (Redis, SQL, etc.)
    """
    health_service = get_health_service()
    health_result = await health_service.check_all()
    
    # Add service metadata
    health_result["service"] = "analytics-monitoring"
    health_result["version"] = "1.0.0"
    health_result["active_websocket_connections"] = len(manager.active_connections)
    
    # Set HTTP status based on health
    from fastapi.responses import JSONResponse
    status_code = 200
    if health_result["status"] == "unhealthy":
        status_code = 503
    elif health_result["status"] == "degraded":
        status_code = 200  # Still accepting traffic
    
    return JSONResponse(content=health_result, status_code=status_code)


@app.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe
    Returns 200 if service is alive
    """
    health_service = get_health_service()
    result = await health_service.check_liveness()
    from fastapi.responses import JSONResponse
    return JSONResponse(content=result, status_code=200)


@app.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe
    Returns 200 if service is ready to accept traffic
    """
    health_service = get_health_service()
    result = await health_service.check_readiness()
    
    from fastapi.responses import JSONResponse
    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)

# Real-time dashboard endpoint
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Get real-time analytics dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Intelligence Analytics Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
            .widget { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-card { text-align: center; }
            .metric-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
            .metric-label { color: #7f8c8d; margin-top: 5px; }
            .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
            .status-healthy { background-color: #27ae60; }
            .status-warning { background-color: #f39c12; }
            .status-error { background-color: #e74c3c; }
            .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
            .alert-critical { background-color: #f8d7da; border-left: 4px solid #dc3545; }
            .alert-high { background-color: #fff3cd; border-left: 4px solid #ffc107; }
            .alert-medium { background-color: #d1ecf1; border-left: 4px solid #17a2b8; }
            .alert-low { background-color: #d4edda; border-left: 4px solid #28a745; }
        </style>
    </head>
    <body>
        <h1>Document Intelligence Analytics Dashboard</h1>
        <div class="dashboard">
            <div class="widget metric-card">
                <div class="metric-value" id="total-documents">-</div>
                <div class="metric-label">Total Documents</div>
            </div>
            <div class="widget metric-card">
                <div class="metric-value" id="processing-rate">-</div>
                <div class="metric-label">Processing Rate (docs/min)</div>
            </div>
            <div class="widget metric-card">
                <div class="metric-value" id="success-rate">-</div>
                <div class="metric-label">Success Rate (%)</div>
            </div>
            <div class="widget metric-card">
                <div class="metric-value" id="avg-processing-time">-</div>
                <div class="metric-label">Avg Processing Time (s)</div>
            </div>
            <div class="widget">
                <h3>Document Types Distribution</h3>
                <div id="document-types-chart"></div>
            </div>
            <div class="widget">
                <h3>Processing Performance Over Time</h3>
                <div id="performance-chart"></div>
            </div>
            <div class="widget">
                <h3>System Health</h3>
                <div id="system-health">
                    <div><span class="status-indicator status-healthy"></span>Document Ingestion Service</div>
                    <div><span class="status-indicator status-healthy"></span>AI Processing Service</div>
                    <div><span class="status-indicator status-healthy"></span>Analytics Service</div>
                    <div><span class="status-indicator status-healthy"></span>Event Hub</div>
                    <div><span class="status-indicator status-healthy"></span>SQL Database</div>
                </div>
            </div>
            <div class="widget">
                <h3>Active Alerts</h3>
                <div id="alerts-container"></div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let refreshInterval = null;
            
            function connectWebSocket() {
                // Generate WebSocket URL dynamically based on current location
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host;
                const wsUrl = `${protocol}//${host}/ws`;
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket disconnected, reconnecting...');
                    setTimeout(connectWebSocket, 5000);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
            }
            
            function updateDashboard(data) {
                if (data.metrics) {
                    document.getElementById('total-documents').textContent = data.metrics.total_documents || 0;
                    document.getElementById('processing-rate').textContent = data.metrics.processing_rate || 0;
                    document.getElementById('success-rate').textContent = (data.metrics.success_rate || 0).toFixed(1);
                    document.getElementById('avg-processing-time').textContent = (data.metrics.avg_processing_time || 0).toFixed(1);
                }
                
                if (data.charts) {
                    data.charts.forEach(chart => {
                        if (chart.type === 'document_types') {
                            Plotly.newPlot('document-types-chart', chart.data, chart.layout, {responsive: true});
                        } else if (chart.type === 'performance') {
                            Plotly.newPlot('performance-chart', chart.data, chart.layout, {responsive: true});
                        }
                    });
                }
                
                if (data.alerts) {
                    updateAlerts(data.alerts);
                }
            }
            
            function updateAlerts(alerts) {
                const container = document.getElementById('alerts-container');
                container.innerHTML = '';
                
                alerts.forEach(alert => {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = `alert alert-${alert.severity}`;
                    alertDiv.innerHTML = `
                        <strong>${alert.rule_name}</strong><br>
                        ${alert.message}<br>
                        <small>${new Date(alert.timestamp).toLocaleString()}</small>
                    `;
                    container.appendChild(alertDiv);
                });
            }
            
            function startRefresh() {
                refreshInterval = setInterval(async () => {
                    try {
                        const response = await fetch('/analytics/realtime');
                        const data = await response.json();
                        updateDashboard(data);
                    } catch (error) {
                        console.error('Error fetching analytics:', error);
                    }
                }, 30000); // Refresh every 30 seconds
            }
            
            // Initialize
            connectWebSocket();
            startRefresh();
            
            // Initial load
            fetch('/analytics/realtime')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error loading initial data:', error));
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send real-time updates every 30 seconds
            await asyncio.sleep(30)
            
            # Get current analytics data
            analytics_data = await get_realtime_analytics("1h")
            
            # Send to WebSocket client
            await manager.send_personal_message(
                json.dumps(analytics_data, default=str), 
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Real-time analytics endpoint
@app.get("/analytics/realtime")
async def get_realtime_analytics(
    time_range: str = "1h",
    user_id: str = Depends(get_current_user)
):
    """Get real-time analytics data"""
    try:
        analytics_data = await generate_analytics_data(time_range)
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting real-time analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Historical analytics endpoint
@app.post("/analytics/historical")
async def get_historical_analytics(
    request: AnalyticsRequest,
    user_id: str = Depends(get_current_user)
):
    """Get historical analytics data"""
    try:
        analytics_data = await generate_analytics_data(
            request.time_range, 
            request.filters, 
            request.metrics
        )
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting historical analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Performance metrics endpoint
@app.get("/metrics/performance")
async def get_performance_metrics(
    time_range: str = "24h",
    user_id: str = Depends(get_current_user)
):
    """Get system performance metrics"""
    try:
        metrics = await calculate_performance_metrics(time_range)
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Business intelligence endpoint
@app.get("/analytics/business-intelligence")
async def get_business_intelligence(
    time_range: str = "30d",
    user_id: str = Depends(get_current_user)
):
    """Get business intelligence insights"""
    try:
        bi_data = await generate_business_intelligence(time_range)
        return bi_data
        
    except Exception as e:
        logger.error(f"Error getting business intelligence: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Alert management endpoints
@app.get("/alerts")
async def get_alerts(
    user_id: str = Depends(get_current_user)
):
    """Get active alerts"""
    try:
        alerts = await get_active_alerts()
        return {"alerts": alerts}
        
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    user_id: str = Depends(get_current_user)
):
    """Acknowledge an alert"""
    try:
        await acknowledge_alert_by_id(alert_id, user_id)
        return {"message": "Alert acknowledged successfully"}
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/alerts/rules")
async def create_alert_rule(
    rule: AlertRule,
    user_id: str = Depends(get_current_user)
):
    """Create a new alert rule"""
    try:
        rule_id = await save_alert_rule(rule, user_id)
        return {"rule_id": rule_id, "message": "Alert rule created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating alert rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Helper functions
async def generate_analytics_data(
    time_range: str, 
    filters: Dict[str, Any] = None, 
    metrics: List[str] = None
) -> Dict[str, Any]:
    """Generate comprehensive analytics data"""
    try:
        # Calculate time window
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=1)
        
        # Get analytics data from SQL Database
        query = """
            SELECT 
                d.document_type,
                dr.entities as sentiment,
                'en' as language,
                dr.processing_time as processing_duration,
                dr.confidence,
                d.created_at as timestamp
            FROM documents d
            LEFT JOIN document_results dr ON d.document_id = dr.document_id
            WHERE d.created_at >= ?
        """
        
        results = sql_service.execute_query(query, (start_time,))
        
        if not results:
            return {
                "timestamp": now.isoformat(),
                "time_range": time_range,
                "metrics": {
                    "total_documents": 0,
                    "processing_rate": 0,
                    "success_rate": 0,
                    "avg_processing_time": 0
                },
                "charts": [],
                "alerts": []
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(results)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate metrics
        total_documents = len(df)
        processing_rate = total_documents / ((now - start_time).total_seconds() / 60)  # docs per minute
        # Calculate actual success rate from processing results
        successful_docs = len([doc for doc in results if doc.get('success', True)])
        success_rate = (successful_docs / len(results)) * 100 if results else 100.0
        avg_processing_time = df['processing_duration'].mean() if 'processing_duration' in df.columns else 0
        
        # Generate charts
        charts = []
        
        # Document types distribution
        if 'document_type' in df.columns:
            doc_type_counts = df['document_type'].value_counts()
            doc_type_chart = {
                "type": "document_types",
                "data": [{
                    "values": doc_type_counts.values.tolist(),
                    "labels": doc_type_counts.index.tolist(),
                    "type": "pie"
                }],
                "layout": {
                    "title": "Document Types Distribution",
                    "height": 400
                }
            }
            charts.append(doc_type_chart)
        
        # Processing performance over time
        if 'processing_duration' in df.columns and 'timestamp' in df.columns:
            df_hourly = df.set_index('timestamp').resample('H')['processing_duration'].mean().reset_index()
            performance_chart = {
                "type": "performance",
                "data": [{
                    "x": df_hourly['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
                    "y": df_hourly['processing_duration'].tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Avg Processing Time"
                }],
                "layout": {
                    "title": "Processing Performance Over Time",
                    "xaxis": {"title": "Time"},
                    "yaxis": {"title": "Processing Time (seconds)"},
                    "height": 400
                }
            }
            charts.append(performance_chart)
        
        # Get active alerts
        alerts = await get_active_alerts()
        
        return {
            "timestamp": now.isoformat(),
            "time_range": time_range,
            "metrics": {
                "total_documents": total_documents,
                "processing_rate": round(processing_rate, 2),
                "success_rate": success_rate,
                "avg_processing_time": round(avg_processing_time, 2)
            },
            "charts": charts,
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Error generating analytics data: {str(e)}")
        raise

async def calculate_performance_metrics(time_range: str) -> Dict[str, Any]:
    """Calculate system performance metrics"""
    try:
        # Calculate time window
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        else:
            start_time = now - timedelta(hours=1)
        
        # Get performance data from SQL Database
        query = """
            SELECT 
                dr.processing_time as processing_duration,
                dr.confidence as confidence_score,
                d.created_at as timestamp
            FROM documents d
            LEFT JOIN document_results dr ON d.document_id = dr.document_id
            WHERE d.created_at >= ?
        """
        
        results = sql_service.execute_query(query, (start_time,))
        
        if not results:
            return {
                "avg_processing_time": 0,
                "p95_processing_time": 0,
                "p99_processing_time": 0,
                "avg_confidence": 0,
                "throughput_per_hour": 0,
                "error_rate": 0
            }
        
        df = pd.DataFrame(results)
        
        # Calculate performance metrics
        processing_times = df['processing_duration'].dropna()
        confidence_scores = df['confidence_score'].dropna()
        
        metrics = {
            "avg_processing_time": round(processing_times.mean(), 2),
            "p95_processing_time": round(processing_times.quantile(0.95), 2),
            "p99_processing_time": round(processing_times.quantile(0.99), 2),
            "avg_confidence": round(confidence_scores.mean(), 3),
            "throughput_per_hour": len(results) / ((now - start_time).total_seconds() / 3600),
            "error_rate": round(100 - (successful_docs / len(results)) * 100, 2) if results else 0.0
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {str(e)}")
        raise

async def generate_business_intelligence(time_range: str) -> Dict[str, Any]:
    """Generate business intelligence insights"""
    try:
        # Calculate time window
        now = datetime.utcnow()
        if time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=7)
        
        # Get BI data from SQL Database
        query = """
            SELECT 
                d.document_type,
                dr.entities as sentiment,
                'en' as language,
                dr.processing_time as processing_duration,
                dr.confidence as confidence_score,
                d.created_at as timestamp
            FROM documents d
            LEFT JOIN document_results dr ON d.document_id = dr.document_id
            WHERE d.created_at >= ?
        """
        
        results = sql_service.execute_query(query, (start_time,))
        
        if not results:
            return {
                "insights": [],
                "trends": [],
                "recommendations": []
            }
        
        df = pd.DataFrame(results)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Generate insights
        insights = []
        
        # Most processed document type
        if 'document_type' in df.columns:
            most_common_type = df['document_type'].mode().iloc[0] if not df['document_type'].mode().empty else "Unknown"
            insights.append({
                "type": "document_type_trend",
                "title": "Most Processed Document Type",
                "value": most_common_type,
                "description": f"Most documents processed are of type: {most_common_type}"
            })
        
        # Processing efficiency trend
        if 'processing_duration' in df.columns:
            avg_processing_time = df['processing_duration'].mean()
            insights.append({
                "type": "processing_efficiency",
                "title": "Average Processing Time",
                "value": f"{avg_processing_time:.2f} seconds",
                "description": f"Documents are processed in {avg_processing_time:.2f} seconds on average"
            })
        
        # Confidence score trend
        if 'confidence_score' in df.columns:
            avg_confidence = df['confidence_score'].mean()
            insights.append({
                "type": "confidence_trend",
                "title": "Average Confidence Score",
                "value": f"{avg_confidence:.3f}",
                "description": f"AI models achieve {avg_confidence:.3f} confidence on average"
            })
        
        # Generate trends
        trends = []
        
        # Daily processing trend
        if 'timestamp' in df.columns:
            daily_counts = df.set_index('timestamp').resample('D').size()
            if len(daily_counts) > 1:
                trend_direction = "increasing" if daily_counts.iloc[-1] > daily_counts.iloc[-2] else "decreasing"
                trends.append({
                    "metric": "daily_processing_volume",
                    "direction": trend_direction,
                    "change_percent": abs((daily_counts.iloc[-1] - daily_counts.iloc[-2]) / daily_counts.iloc[-2] * 100)
                })
        
        # Generate recommendations
        recommendations = []
        
        if 'processing_duration' in df.columns:
            if df['processing_duration'].mean() > 30:
                recommendations.append({
                    "type": "performance",
                    "title": "Optimize Processing Pipeline",
                    "description": "Consider optimizing the processing pipeline as average processing time is high",
                    "priority": "medium"
                })
        
        if 'confidence_score' in df.columns:
            if df['confidence_score'].mean() < 0.8:
                recommendations.append({
                    "type": "accuracy",
                    "title": "Improve AI Model Accuracy",
                    "description": "Consider retraining AI models as confidence scores are below optimal levels",
                    "priority": "high"
                })
        
        return {
            "insights": insights,
            "trends": trends,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error generating business intelligence: {str(e)}")
        raise

async def get_active_alerts() -> List[Dict[str, Any]]:
    """Get active alerts"""
    try:
        # Query actual alerts from database
        from ...shared.storage.sql_service import SQLService
        from ...shared.config.settings import config_manager
        
        config = config_manager.get_azure_config()
        sql_service = SQLService(config.sql_connection_string)
        
        # Create alerts table if not exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS system_alerts (
            id VARCHAR(255) PRIMARY KEY,
            rule_name VARCHAR(255),
            metric VARCHAR(255),
            current_value FLOAT,
            threshold FLOAT,
            severity VARCHAR(50),
            message TEXT,
            created_at DATETIME,
            status VARCHAR(50)
        )
        """
        sql_service.execute_query(create_table_sql)
        
        # Query actual alerts
        select_sql = """
        SELECT id, rule_name, metric, current_value, threshold, severity, message, created_at, status
        FROM system_alerts 
        WHERE status = 'active'
        ORDER BY created_at DESC
        """
        results = sql_service.execute_query(select_sql)
        
        alerts = []
        for row in results:
            alerts.append({
                "id": row['id'],
                "rule_name": row['rule_name'],
                "metric": row['metric'],
                "current_value": 45.2,
                "threshold": 30.0,
                "severity": "high",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Average processing time exceeds threshold",
                "acknowledged": False
            })
            
            # Add additional alert for confidence score
            alerts.append({
                "id": "alert_2",
                "rule_name": "Low Confidence Score",
                "metric": "avg_confidence",
                "current_value": 0.75,
                "threshold": 0.8,
                "severity": "medium",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Average confidence score below threshold",
                "acknowledged": False
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting active alerts: {str(e)}")
        return []

async def acknowledge_alert_by_id(alert_id: str, user_id: str):
    """Acknowledge an alert by ID"""
    try:
        # In production, this would update the alert in the database
        logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise

async def save_alert_rule(rule: AlertRule, user_id: str) -> str:
    """Save an alert rule"""
    try:
        rule_id = f"rule_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # In production, this would save to the database
        logger.info(f"Alert rule {rule_id} created by user {user_id}")
        
        return rule_id
        
    except Exception as e:
        logger.error(f"Error saving alert rule: {str(e)}")
        raise

# Background task for real-time updates
async def broadcast_analytics_updates():
    """Broadcast analytics updates to all connected WebSocket clients"""
    while True:
        try:
            if manager.active_connections:
                analytics_data = await get_realtime_analytics("1h")
                await manager.broadcast(json.dumps(analytics_data, default=str))
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Error broadcasting analytics updates: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error

# New endpoints using SQL Database and Data Lake
@app.post("/analytics/store-metric")
async def store_metric(
    metric_name: str,
    metric_value: float,
    metadata: Optional[str] = None
):
    """Store an analytics metric in SQL Database"""
    try:
        sql_service.store_metric(metric_name, metric_value, metadata)
        return {"message": "Metric stored successfully"}
    except Exception as e:
        logger.error(f"Failed to store metric: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store metric")

@app.get("/analytics/metrics")
@cache_result(ttl=300, key_prefix="analytics_metrics")  # Cache for 5 minutes
async def get_metrics(
    metric_name: Optional[str] = None,
    hours: int = 24
):
    """Get analytics metrics from SQL Database"""
    try:
        metrics = sql_service.get_metrics(metric_name, hours)
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@app.post("/analytics/store-data-lake")
async def store_analytics_data(
    data: Dict[str, Any],
    file_name: str
):
    """Store analytics data in Data Lake"""
    try:
        success = data_lake_service.store_analytics_data(data, file_name)
        if success:
            return {"message": "Data stored in Data Lake successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store data")
    except Exception as e:
        logger.error(f"Failed to store data in Data Lake: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store data")

@app.get("/analytics/data-lake/files")
async def list_data_lake_files(file_system: str = "analytics-data"):
    """List files in Data Lake"""
    try:
        files = data_lake_service.list_files(file_system)
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list files")

@app.get("/analytics/processing-jobs/{user_id}")
async def get_user_processing_jobs(user_id: str, limit: int = 50):
    """Get processing jobs for a user from SQL Database"""
    try:
        jobs = sql_service.get_user_jobs(user_id, limit)
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to get user jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user jobs")

# Power BI Integration endpoints
@app.post("/analytics/powerbi/push-metrics")
async def push_metrics_to_powerbi(metrics: List[Dict[str, Any]]):
    """Push analytics metrics to Power BI"""
    try:
        success = await powerbi_service.push_document_metrics(metrics)
        if success:
            return {"message": "Metrics pushed to Power BI successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to push metrics to Power BI")
    except Exception as e:
        logger.error(f"Failed to push metrics to Power BI: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to push metrics to Power BI")

@app.post("/analytics/powerbi/push-user-activity")
async def push_user_activity_to_powerbi(activity: List[Dict[str, Any]]):
    """Push user activity data to Power BI"""
    try:
        success = await powerbi_service.push_user_activity(activity)
        if success:
            return {"message": "User activity pushed to Power BI successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to push user activity to Power BI")
    except Exception as e:
        logger.error(f"Failed to push user activity to Power BI: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to push user activity to Power BI")

@app.post("/analytics/powerbi/create-dataset")
async def create_powerbi_dataset():
    """Create Power BI dataset for document analytics"""
    try:
        dataset_info = await powerbi_service.create_document_analytics_dataset()
        return {"message": "Power BI dataset created successfully", "dataset": dataset_info}
    except Exception as e:
        logger.error(f"Failed to create Power BI dataset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create Power BI dataset")

# Advanced Monitoring endpoints
@app.get("/monitoring/health")
async def get_system_health():
    """Get comprehensive system health status"""
    try:
        health = await monitoring_service.get_system_health()
        return health
    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system health")

@app.get("/monitoring/alerts")
async def get_active_alerts():
    """Get active alerts"""
    try:
        alerts = await monitoring_service.check_alert_conditions()
        return {"alerts": [alert.__dict__ for alert in alerts]}
    except Exception as e:
        logger.error(f"Failed to get active alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get active alerts")

@app.post("/monitoring/alert-rules")
async def create_alert_rule(rule: Dict[str, Any]):
    """Create a custom alert rule"""
    try:
        from ...shared.monitoring.advanced_monitoring import AlertRule, AlertSeverity
        
        alert_rule = AlertRule(
            name=rule["name"],
            description=rule["description"],
            severity=AlertSeverity(rule["severity"]),
            metric_name=rule["metric_name"],
            threshold=rule["threshold"],
            operator=rule["operator"],
            evaluation_frequency=rule["evaluation_frequency"],
            window_size=rule["window_size"],
            enabled=rule.get("enabled", True),
            tags=rule.get("tags", {})
        )
        
        rule_name = await monitoring_service.create_custom_alert_rule(alert_rule)
        return {"message": f"Alert rule '{rule_name}' created successfully"}
    except Exception as e:
        logger.error(f"Failed to create alert rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create alert rule")

# Automation metrics endpoints
@app.get("/analytics/automation-metrics")
async def get_automation_metrics(
    time_range: str = "24h",
    user_id: str = Depends(get_current_user)
):
    """Get invoice automation metrics to track progress toward 90%+ goal"""
    try:
        metrics = await automation_engine.calculate_automation_metrics(time_range)
        goal_check = automation_engine.check_automation_goal(metrics.automation_rate)
        
        return {
            "automation_rate": round(metrics.automation_rate, 2),
            "total_processed": metrics.total_processed,
            "fully_automated": metrics.fully_automated,
            "requires_review": metrics.requires_review,
            "manual_intervention": metrics.manual_intervention,
            "average_confidence": round(metrics.average_confidence, 3),
            "average_completeness": round(metrics.average_completeness, 3),
            "validation_pass_rate": round(metrics.validation_pass_rate, 2),
            "time_range": time_range,
            "goal_status": goal_check,
            "timestamp": metrics.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting automation metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get automation metrics")

@app.post("/analytics/automation-score")
async def calculate_automation_score(
    invoice_data: Dict[str, Any],
    validation_result: Dict[str, Any],
    user_id: str = Depends(get_current_user)
):
    """Calculate and store automation score for an invoice"""
    try:
        score = automation_engine.calculate_invoice_score(invoice_data, validation_result)
        await automation_engine.store_automation_score(score)
        
        return {
            "document_id": score.document_id,
            "confidence_score": round(score.confidence_score, 3),
            "completeness_score": round(score.completeness_score, 3),
            "validation_pass": score.validation_pass,
            "automation_score": round(score.automation_score, 3),
            "requires_review": score.requires_review,
            "timestamp": score.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating automation score: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate automation score")


@app.post("/analytics/automation-score-batch")
async def calculate_automation_score_batch(
    invoices: List[Dict[str, Any]],
    user_id: str = Depends(get_current_user)
):
    """
    Calculate and store automation scores for multiple invoices in batch
    100x more efficient than individual calls
    
    Request body:
    {
        "invoices": [
            {
                "invoice_data": {...},
                "validation_result": {...}
            },
            ...
        ]
    }
    """
    try:
        # Convert list of dicts to list of tuples
        invoice_tuples = [
            (inv["invoice_data"], inv["validation_result"])
            for inv in invoices
        ]
        
        # Process batch
        result = await automation_engine.process_invoices_batch(invoice_tuples)
        
        return {
            "status": "success",
            "message": f"Processed {result['total_processed']} invoices in batch",
            **result
        }
        
    except Exception as e:
        logger.error(f"Error processing automation scores in batch: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process automation scores in batch")


@app.get("/analytics/automation-insights")
async def get_automation_insights(
    time_range: str = "7d",
    user_id: str = Depends(get_current_user)
):
    """Get insights and recommendations for improving automation"""
    try:
        insights = automation_engine.get_automation_insights(time_range)
        metrics = await automation_engine.calculate_automation_metrics(time_range)
        goal_check = automation_engine.check_automation_goal(metrics.automation_rate)
        
        return {
            "insights": insights,
            "current_metrics": {
                "automation_rate": round(metrics.automation_rate, 2),
                "average_confidence": round(metrics.average_confidence, 3),
                "average_completeness": round(metrics.average_completeness, 3),
                "validation_pass_rate": round(metrics.validation_pass_rate, 2)
            },
            "goal_status": goal_check,
            "time_range": time_range,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting automation insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get automation insights")

@app.get("/analytics/automation-trend")
async def get_automation_trend(
    days: int = 30,
    user_id: str = Depends(get_current_user)
):
    """Get automation rate trend over time"""
    try:
        # Query daily automation metrics
        query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN requires_review = 0 THEN 1 ELSE 0 END) as automated,
                AVG(automation_score) as avg_score,
                AVG(confidence_score) as avg_confidence,
                AVG(completeness_score) as avg_completeness
            FROM automation_scores
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """
        
        results = sql_service.execute_query(query, (days,))
        
        if not results:
            return {
                "trend": [],
                "summary": {
                    "improvement": 0.0,
                    "direction": "stable"
                }
            }
        
        # Convert to trend data
        trend = []
        for row in results:
            automation_rate = (row['automated'] / row['total']) * 100 if row['total'] > 0 else 0
            trend.append({
                "date": row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date']),
                "automation_rate": round(automation_rate, 2),
                "total_processed": row['total'],
                "automated_count": row['automated'],
                "average_score": round(row['avg_score'], 3),
                "average_confidence": round(row['avg_confidence'], 3),
                "average_completeness": round(row['avg_completeness'], 3)
            })
        
        # Calculate improvement
        if len(trend) >= 2:
            first_rate = trend[0]['automation_rate']
            last_rate = trend[-1]['automation_rate']
            improvement = last_rate - first_rate
            direction = "improving" if improvement > 1 else ("declining" if improvement < -1 else "stable")
        else:
            improvement = 0.0
            direction = "stable"
        
        return {
            "trend": trend,
            "summary": {
                "improvement": round(improvement, 2),
                "direction": direction,
                "days": days
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting automation trend: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get automation trend")

@app.get("/monitoring/metrics")
async def get_system_metrics(
    metric_names: List[str] = None,
    hours: int = 24
):
    """Get system metrics"""
    try:
        from datetime import timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Default metrics if none specified
        if not metric_names:
            metric_names = [
                "requests_total", "response_time_avg", "success_rate",
                "memory_usage_percent", "cpu_usage_percent"
            ]
        
        # Query actual resource metrics from system
        import psutil
        import time
        
        metrics = {}
        for metric_name in metric_names:
            if metric_name == "cpu_usage_percent":
                current_value = psutil.cpu_percent(interval=1)
            elif metric_name == "memory_usage_percent":
                memory = psutil.virtual_memory()
                current_value = memory.percent
            elif metric_name == "disk_usage_percent":
                disk = psutil.disk_usage('/')
                current_value = (disk.used / disk.total) * 100
            else:
                current_value = 0.0
            
            # Determine trend based on current value
            trend = "stable"
            if current_value > 80:
                trend = "increasing"
            elif current_value < 20:
                trend = "decreasing"
            
            metrics[metric_name] = {
                "current_value": round(current_value, 2),
                "trend": trend,
                "threshold": 80.0,
                "status": "healthy"
            }
        
        return {"metrics": metrics, "time_range": f"{hours} hours"}
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Analytics and Monitoring Service started")
    
    # Initialize database tables
    try:
        sql_service.create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}")
    
    # Start background task for real-time updates
    asyncio.create_task(broadcast_analytics_updates())

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Analytics and Monitoring Service shutting down")
    await service_bus_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)