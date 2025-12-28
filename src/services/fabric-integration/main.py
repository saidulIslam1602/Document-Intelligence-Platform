"""
Fabric Integration Service API
Main API for Microsoft Fabric integration
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

# Pydantic models must be defined before imports
class OneLakeWorkspace(BaseModel):
    id: str
    name: str
    type: str = "workspace"

class OneLakeItem(BaseModel):
    id: str
    name: str
    type: str

class WarehouseInfo(BaseModel):
    name: str
    id: str
    status: str = "active"

class QueryResult(BaseModel):
    rows: List[Dict[str, Any]] = []
    columns: List[str] = []

try:
    from onelake_connector import OneLakeConnector
    from fabric_warehouse import FabricWarehouseService
    FABRIC_AVAILABLE = True
except ImportError:
    FABRIC_AVAILABLE = False
    class OneLakeConnector:
        def __init__(self):
            pass
    class FabricWarehouseService:
        def __init__(self):
            pass

# Initialize FastAPI app
app = FastAPI(
    title="Fabric Integration Service",
    description="Microsoft Fabric integration service for OneLake, Data Warehouse, and Power BI",
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

# Fabric services
onelake_connector = OneLakeConnector()
fabric_warehouse_service = FabricWarehouseService()

# Pydantic models
class LakehouseCreateRequest(BaseModel):
    name: str = Field(..., description="Lakehouse name")
    description: str = Field(None, description="Lakehouse description")

class TableCreateRequest(BaseModel):
    lakehouse_name: str = Field(..., description="Lakehouse name")
    table_name: str = Field(..., description="Table name")
    schema: Dict[str, str] = Field(..., description="Table schema")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Initial data")

class WarehouseCreateRequest(BaseModel):
    name: str = Field(..., description="Warehouse name")
    compute_tier: str = Field(default="Serverless", description="Compute tier")
    max_size_gb: int = Field(default=100, description="Maximum size in GB")

class SQLQueryRequest(BaseModel):
    warehouse_name: str = Field(..., description="Warehouse name")
    query: str = Field(..., description="SQL query to execute")

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
    return {"status": "healthy", "service": "fabric-integration"}

# OneLake endpoints
@app.get("/onelake/workspaces")
async def list_workspaces(current_user: User = Depends(get_current_user)) -> List[OneLakeWorkspace]:
    """List all OneLake workspaces"""
    try:
        workspaces = await onelake_connector.list_workspaces()
        return workspaces
    except Exception as e:
        logger.error(f"Error listing workspaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {str(e)}")

@app.post("/onelake/lakehouses")
async def create_lakehouse(
    request: LakehouseCreateRequest,
    current_user: User = Depends(get_current_user)
) -> OneLakeItem:
    """Create a new OneLake lakehouse"""
    try:
        lakehouse = await onelake_connector.create_lakehouse(
            request.name,
            request.description
        )
        return lakehouse
    except Exception as e:
        logger.error(f"Error creating lakehouse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create lakehouse: {str(e)}")

@app.get("/onelake/lakehouses/{lakehouse_name}")
async def get_lakehouse_info(
    lakehouse_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get lakehouse information"""
    try:
        info = await onelake_connector.get_lakehouse_info(lakehouse_name)
        return info
    except Exception as e:
        logger.error(f"Error getting lakehouse info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get lakehouse info: {str(e)}")

@app.post("/onelake/tables")
async def create_table(
    request: TableCreateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a table in OneLake lakehouse"""
    try:
        import pandas as pd
        
        data_df = None
        if request.data:
            data_df = pd.DataFrame(request.data)
        
        result = await onelake_connector.create_table(
            request.lakehouse_name,
            request.table_name,
            request.schema,
            data_df
        )
        return result
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")

@app.get("/onelake/lakehouses/{lakehouse_name}/tables")
async def list_tables(
    lakehouse_name: str,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List tables in a lakehouse"""
    try:
        tables = await onelake_connector.list_tables(lakehouse_name)
        return tables
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")

@app.post("/onelake/query")
async def query_table(
    lakehouse_name: str,
    table_name: str,
    query: str = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Query a table in OneLake lakehouse"""
    try:
        import pandas as pd
        
        df = await onelake_connector.query_table(lakehouse_name, table_name, query)
        
        return {
            "lakehouse": lakehouse_name,
            "table": table_name,
            "query": query,
            "row_count": len(df),
            "columns": list(df.columns),
            "data": df.to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error querying table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to query table: {str(e)}")

# Fabric Data Warehouse endpoints
@app.post("/warehouse/create")
async def create_warehouse(
    request: WarehouseCreateRequest,
    current_user: User = Depends(get_current_user)
) -> WarehouseInfo:
    """Create a new Fabric Data Warehouse"""
    try:
        warehouse = await fabric_warehouse_service.create_warehouse(
            request.name,
            request.compute_tier,
            request.max_size_gb
        )
        return warehouse
    except Exception as e:
        logger.error(f"Error creating warehouse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create warehouse: {str(e)}")

@app.get("/warehouse/{warehouse_name}")
async def get_warehouse_info(
    warehouse_name: str,
    current_user: User = Depends(get_current_user)
) -> WarehouseInfo:
    """Get warehouse information"""
    try:
        warehouse = await fabric_warehouse_service.get_warehouse_info(warehouse_name)
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        return warehouse
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warehouse info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get warehouse info: {str(e)}")

@app.post("/warehouse/query")
async def execute_sql_query(
    request: SQLQueryRequest,
    current_user: User = Depends(get_current_user)
) -> QueryResult:
    """Execute SQL query on warehouse"""
    try:
        result = await fabric_warehouse_service.execute_sql_query(
            request.warehouse_name,
            request.query
        )
        return result
    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to execute query: {str(e)}")

@app.post("/warehouse/{warehouse_name}/tables")
async def create_warehouse_table(
    warehouse_name: str,
    table_name: str,
    schema: Dict[str, str],
    primary_key: str = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a table in the warehouse"""
    try:
        result = await fabric_warehouse_service.create_table(
            warehouse_name,
            table_name,
            schema,
            primary_key
        )
        return result
    except Exception as e:
        logger.error(f"Error creating warehouse table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")

@app.post("/warehouse/{warehouse_name}/tables/{table_name}/data")
async def insert_warehouse_data(
    warehouse_name: str,
    table_name: str,
    data: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Insert data into warehouse table"""
    try:
        result = await fabric_warehouse_service.insert_data(
            warehouse_name,
            table_name,
            data
        )
        return result
    except Exception as e:
        logger.error(f"Error inserting warehouse data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to insert data: {str(e)}")

@app.get("/warehouse/{warehouse_name}/metrics")
async def get_warehouse_metrics(
    warehouse_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get warehouse performance metrics"""
    try:
        metrics = await fabric_warehouse_service.get_warehouse_metrics(warehouse_name)
        return metrics
    except Exception as e:
        logger.error(f"Error getting warehouse metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.post("/warehouse/{warehouse_name}/pause")
async def pause_warehouse(
    warehouse_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Pause the warehouse"""
    try:
        result = await fabric_warehouse_service.pause_warehouse(warehouse_name)
        return result
    except Exception as e:
        logger.error(f"Error pausing warehouse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to pause warehouse: {str(e)}")

@app.post("/warehouse/{warehouse_name}/resume")
async def resume_warehouse(
    warehouse_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resume the warehouse"""
    try:
        result = await fabric_warehouse_service.resume_warehouse(warehouse_name)
        return result
    except Exception as e:
        logger.error(f"Error resuming warehouse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to resume warehouse: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)