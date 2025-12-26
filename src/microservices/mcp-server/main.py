"""
MCP (Model Context Protocol) Server Microservice
Exposes Document Intelligence Platform capabilities as MCP-compliant tools for AI agents
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import httpx

from ...shared.config.settings import config_manager
from .mcp_tools import MCPToolRegistry
from .mcp_resources import MCPResourceManager

# Initialize FastAPI app
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol server for Document Intelligence Platform",
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

# Service endpoints
SERVICE_ENDPOINTS = {
    "ai-processing": "http://ai-processing:8001",
    "data-quality": "http://data-quality:8006",
    "analytics": "http://analytics:8002",
    "document-ingestion": "http://document-ingestion:8000",
    "ai-chat": "http://ai-chat:8004"
}

# Initialize MCP components
tool_registry = MCPToolRegistry(SERVICE_ENDPOINTS)
resource_manager = MCPResourceManager(SERVICE_ENDPOINTS)

# Pydantic models
class MCPToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MCPToolResponse(BaseModel):
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float
    timestamp: datetime

class MCPResourceRequest(BaseModel):
    resource_uri: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MCPResourceResponse(BaseModel):
    resource_uri: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime

class MCPCapabilitiesResponse(BaseModel):
    server_name: str
    server_version: str
    protocol_version: str
    capabilities: Dict[str, Any]
    tools: List[Dict[str, Any]]
    resources: List[Dict[str, Any]]

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
        "service": "mcp-server",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "protocol_version": "0.9.0",
        "tools_count": len(tool_registry.get_available_tools()),
        "resources_count": len(resource_manager.get_available_resources())
    }

# MCP capabilities endpoint
@app.get("/mcp/capabilities", response_model=MCPCapabilitiesResponse)
async def get_mcp_capabilities():
    """Get MCP server capabilities"""
    try:
        available_tools = tool_registry.get_available_tools()
        available_resources = resource_manager.get_available_resources()
        
        return MCPCapabilitiesResponse(
            server_name="Document Intelligence Platform MCP Server",
            server_version="1.0.0",
            protocol_version="0.9.0",
            capabilities={
                "tools": {
                    "supported": True,
                    "count": len(available_tools)
                },
                "resources": {
                    "supported": True,
                    "count": len(available_resources),
                    "subscribe": False
                },
                "prompts": {
                    "supported": False
                },
                "logging": {
                    "supported": True
                }
            },
            tools=available_tools,
            resources=available_resources
        )
        
    except Exception as e:
        logger.error(f"Error getting MCP capabilities: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# List tools endpoint
@app.get("/mcp/tools")
async def list_tools():
    """List all available MCP tools"""
    try:
        tools = tool_registry.get_available_tools()
        return {
            "tools": tools,
            "count": len(tools)
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Execute tool endpoint
@app.post("/mcp/tools/execute", response_model=MCPToolResponse)
async def execute_tool(
    request: MCPToolRequest,
    user_id: str = Depends(get_current_user)
):
    """Execute an MCP tool"""
    try:
        start_time = datetime.utcnow()
        
        # Execute tool
        result = await tool_registry.execute_tool(
            request.tool_name,
            request.parameters,
            request.context
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return MCPToolResponse(
            tool_name=request.tool_name,
            success=True,
            result=result,
            execution_time=execution_time,
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.error(f"Invalid tool request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {str(e)}")
        return MCPToolResponse(
            tool_name=request.tool_name,
            success=False,
            error=str(e),
            execution_time=0.0,
            timestamp=datetime.utcnow()
        )

# List resources endpoint
@app.get("/mcp/resources")
async def list_resources():
    """List all available MCP resources"""
    try:
        resources = resource_manager.get_available_resources()
        return {
            "resources": resources,
            "count": len(resources)
        }
        
    except Exception as e:
        logger.error(f"Error listing resources: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Read resource endpoint
@app.post("/mcp/resources/read", response_model=MCPResourceResponse)
async def read_resource(
    request: MCPResourceRequest,
    user_id: str = Depends(get_current_user)
):
    """Read an MCP resource"""
    try:
        # Read resource
        data = await resource_manager.read_resource(
            request.resource_uri,
            request.parameters
        )
        
        return MCPResourceResponse(
            resource_uri=request.resource_uri,
            success=True,
            data=data,
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.error(f"Invalid resource request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading resource {request.resource_uri}: {str(e)}")
        return MCPResourceResponse(
            resource_uri=request.resource_uri,
            success=False,
            error=str(e),
            timestamp=datetime.utcnow()
        )

# Invoice processing tool endpoint (convenience)
@app.post("/mcp/invoice/extract")
async def extract_invoice_data(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Extract invoice data using Form Recognizer (MCP tool wrapper)"""
    try:
        result = await tool_registry.execute_tool(
            "extract_invoice_data",
            {"document_id": document_id},
            {"user_id": user_id}
        )
        return result
        
    except Exception as e:
        logger.error(f"Error extracting invoice data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Invoice validation tool endpoint (convenience)
@app.post("/mcp/invoice/validate")
async def validate_invoice(
    invoice_data: Dict[str, Any],
    user_id: str = Depends(get_current_user)
):
    """Validate invoice data using Data Quality Service (MCP tool wrapper)"""
    try:
        result = await tool_registry.execute_tool(
            "validate_invoice",
            {"invoice_data": invoice_data},
            {"user_id": user_id}
        )
        return result
        
    except Exception as e:
        logger.error(f"Error validating invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Document classification tool endpoint (convenience)
@app.post("/mcp/document/classify")
async def classify_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Classify document using ML models (MCP tool wrapper)"""
    try:
        result = await tool_registry.execute_tool(
            "classify_document",
            {"document_id": document_id},
            {"user_id": user_id}
        )
        return result
        
    except Exception as e:
        logger.error(f"Error classifying document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Automation metrics tool endpoint (convenience)
@app.get("/mcp/metrics/automation")
async def get_automation_metrics(
    time_range: str = "24h",
    user_id: str = Depends(get_current_user)
):
    """Get automation metrics (MCP tool wrapper)"""
    try:
        result = await tool_registry.execute_tool(
            "get_automation_metrics",
            {"time_range": time_range},
            {"user_id": user_id}
        )
        return result
        
    except Exception as e:
        logger.error(f"Error getting automation metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Fine-tuning job tool endpoint (convenience)
@app.post("/mcp/fine-tuning/create-job")
async def create_fine_tuning_job(
    training_file: str,
    model: str = "gpt-3.5-turbo",
    user_id: str = Depends(get_current_user)
):
    """Create fine-tuning job (MCP tool wrapper)"""
    try:
        result = await tool_registry.execute_tool(
            "create_fine_tuning_job",
            {
                "training_file": training_file,
                "model": model
            },
            {"user_id": user_id}
        )
        return result
        
    except Exception as e:
        logger.error(f"Error creating fine-tuning job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# M365 document processing tool endpoint (convenience)
@app.post("/mcp/m365/process-document")
async def process_m365_document(
    document_url: str,
    user_id: str = Depends(get_current_user)
):
    """Process M365 document (MCP tool wrapper)"""
    try:
        result = await tool_registry.execute_tool(
            "process_m365_document",
            {"document_url": document_url},
            {"user_id": user_id}
        )
        return result
        
    except Exception as e:
        logger.error(f"Error processing M365 document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# MCP protocol endpoints (standard)
@app.post("/mcp/initialize")
async def mcp_initialize(request: Request):
    """MCP protocol initialization endpoint"""
    try:
        body = await request.json()
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": "0.9.0",
                "capabilities": {
                    "tools": {"supported": True},
                    "resources": {"supported": True},
                    "prompts": {"supported": False},
                    "logging": {"supported": True}
                },
                "serverInfo": {
                    "name": "Document Intelligence Platform MCP Server",
                    "version": "1.0.0"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in MCP initialize: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mcp/tools/list")
async def mcp_list_tools(request: Request):
    """MCP protocol list tools endpoint"""
    try:
        body = await request.json()
        tools = tool_registry.get_available_tools()
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "tools": tools
            }
        }
        
    except Exception as e:
        logger.error(f"Error in MCP list tools: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mcp/tools/call")
async def mcp_call_tool(request: Request):
    """MCP protocol call tool endpoint"""
    try:
        body = await request.json()
        params = body.get("params", {})
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        result = await tool_registry.execute_tool(tool_name, arguments, {})
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in MCP call tool: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", 1),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

@app.post("/mcp/resources/list")
async def mcp_list_resources(request: Request):
    """MCP protocol list resources endpoint"""
    try:
        body = await request.json()
        resources = resource_manager.get_available_resources()
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "resources": resources
            }
        }
        
    except Exception as e:
        logger.error(f"Error in MCP list resources: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mcp/resources/read")
async def mcp_read_resource(request: Request):
    """MCP protocol read resource endpoint"""
    try:
        body = await request.json()
        params = body.get("params", {})
        
        resource_uri = params.get("uri")
        
        data = await resource_manager.read_resource(resource_uri, {})
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "contents": [
                    {
                        "uri": resource_uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, indent=2)
                    }
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in MCP read resource: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", 1),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("MCP Server started")
    logger.info(f"Registered {len(tool_registry.get_available_tools())} tools")
    logger.info(f"Registered {len(resource_manager.get_available_resources())} resources")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("MCP Server shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)

