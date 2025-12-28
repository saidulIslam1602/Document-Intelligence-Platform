"""
Migration Service API
Main API for database migration operations
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    ServiceBusClient = None
    ServiceBusMessage = None

from src.shared.config.settings import config_manager
from src.shared.auth.auth_service import auth_service, User

try:
    from teradata_migrator import TeradataMigrator, MigrationJob, MigrationStatus
    from netezza_migrator import NetezzaMigrator
    from schema_converter import SchemaConverter, DatabaseType
except ImportError:
    # Stub classes
    class TeradataMigrator:
        pass
    class MigrationJob:
        pass
    class MigrationStatus:
        pass
    class NetezzaMigrator:
        pass
    class SchemaConverter:
        pass
    class DatabaseType:
        pass

# Initialize FastAPI app
app = FastAPI(
    title="Migration Service",
    description="Database migration service for Teradata, Netezza, and Oracle to Azure SQL Database",
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

# Migration services
teradata_migrator = TeradataMigrator()
netezza_migrator = NetezzaMigrator()
schema_converter = SchemaConverter()

# Azure clients
if AZURE_AVAILABLE and hasattr(config, 'service_bus_connection_string') and config.service_bus_connection_string:
    service_bus_client = ServiceBusClient.from_connection_string(
        config.service_bus_connection_string
    )
else:
    service_bus_client = None
    logger.warning("Service Bus not configured - running without messaging capabilities")

# Pydantic models
class MigrationRequest(BaseModel):
    source_system: str = Field(..., description="Source database system")
    target_system: str = Field(default="Azure SQL Database", description="Target database system")
    source_schema: str = Field(..., description="Source schema name")
    target_schema: str = Field(default="dbo", description="Target schema name")
    tables: Optional[List[str]] = Field(None, description="Specific tables to migrate (optional)")
    batch_size: int = Field(default=10000, description="Batch size for data migration")

class SchemaConversionRequest(BaseModel):
    source_ddl: str = Field(..., description="Source DDL to convert")
    source_database_type: str = Field(..., description="Source database type")
    target_schema: str = Field(default="dbo", description="Target schema name")

class MigrationStatusResponse(BaseModel):
    job_id: str
    source_system: str
    target_system: str
    status: str
    progress_percentage: float
    tables_migrated: int
    total_tables: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class SchemaAnalysisResponse(BaseModel):
    tables: List[Dict[str, Any]]
    total_tables: int
    total_size_mb: float
    estimated_migration_time_minutes: int

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
    return {"status": "healthy", "service": "migration-service"}

@app.post("/migration/analyze-schema")
async def analyze_schema(
    source_system: str,
    schema_name: str,
    current_user: User = Depends(get_current_user)
) -> SchemaAnalysisResponse:
    """Analyze source database schema"""
    try:
        logger.info(f"Analyzing schema for {source_system}: {schema_name}")
        
        if source_system.lower() == "teradata":
            tables = await teradata_migrator.analyze_teradata_schema(schema_name)
        elif source_system.lower() == "netezza":
            tables = await netezza_migrator.analyze_netezza_schema(schema_name)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source system: {source_system}")
        
        # Calculate totals
        total_size_mb = sum(table.size_mb for table in tables)
        estimated_time = int(total_size_mb * 0.1)  # Rough estimate: 0.1 minutes per MB
        
        # Convert tables to dict format
        tables_data = []
        for table in tables:
            table_dict = {
                "table_name": table.table_name,
                "schema_name": table.schema_name,
                "column_count": table.column_count,
                "row_count": table.row_count,
                "size_mb": table.size_mb,
                "last_modified": table.last_modified.isoformat(),
                "columns": table.columns
            }
            tables_data.append(table_dict)
        
        return SchemaAnalysisResponse(
            tables=tables_data,
            total_tables=len(tables),
            total_size_mb=total_size_mb,
            estimated_migration_time_minutes=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Error analyzing schema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema analysis failed: {str(e)}")

@app.post("/migration/start")
async def start_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start a new migration job"""
    try:
        logger.info(f"Starting migration from {request.source_system} to {request.target_system}")
        
        # Create migration job
        if request.source_system.lower() == "teradata":
            job = await teradata_migrator.create_migration_job(
                request.source_schema, 
                request.target_schema
            )
        elif request.source_system.lower() == "netezza":
            job = await netezza_migrator.create_migration_job(
                request.source_schema, 
                request.target_schema
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source system: {request.source_system}")
        
        # Start migration in background
        background_tasks.add_task(
            execute_migration_task,
            job.job_id,
            request.source_system,
            request.source_schema
        )
        
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "message": "Migration job started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting migration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start migration: {str(e)}")

async def execute_migration_task(job_id: str, source_system: str, schema_name: str):
    """Execute migration task in background"""
    try:
        if source_system.lower() == "teradata":
            await teradata_migrator.execute_migration(job_id, schema_name)
        elif source_system.lower() == "netezza":
            await netezza_migrator.execute_migration(job_id, schema_name)
        
        # Send completion notification
        await send_migration_notification(job_id, "completed")
        
    except Exception as e:
        logger.error(f"Migration task failed: {str(e)}")
        await send_migration_notification(job_id, "failed", str(e))

async def send_migration_notification(job_id: str, status: str, error_message: str = None):
    """Send migration status notification"""
    try:
        message = {
            "job_id": job_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "error_message": error_message
        }
        
        service_bus_client = ServiceBusClient.from_connection_string(
            config.service_bus_connection_string
        )
        
        with service_bus_client.get_queue_sender(queue_name="migration-notifications") as sender:
            message_obj = ServiceBusMessage(json.dumps(message))
            sender.send_messages(message_obj)
            
    except Exception as e:
        logger.error(f"Failed to send migration notification: {str(e)}")

@app.get("/migration/status/{job_id}")
async def get_migration_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> MigrationStatusResponse:
    """Get migration job status"""
    try:
        # Try to get status from both migrators
        job = await teradata_migrator.get_migration_status(job_id)
        if not job:
            job = await netezza_migrator.get_migration_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Migration job not found")
        
        return MigrationStatusResponse(
            job_id=job.job_id,
            source_system=job.source_system,
            target_system=job.target_system,
            status=job.status.value,
            progress_percentage=job.progress_percentage,
            tables_migrated=job.tables_migrated,
            total_tables=job.total_tables,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting migration status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get migration status: {str(e)}")

@app.get("/migration/jobs")
async def list_migration_jobs(
    current_user: User = Depends(get_current_user)
) -> List[MigrationStatusResponse]:
    """List all migration jobs for the current user"""
    try:
        # This would typically filter by user_id in a real implementation
        # For now, we'll return all jobs
        jobs = []
        
        # Get jobs from database
        # This is a simplified implementation
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing migration jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list migration jobs: {str(e)}")

@app.post("/migration/convert-schema")
async def convert_schema(
    request: SchemaConversionRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Convert DDL from source database to Azure SQL Database"""
    try:
        logger.info(f"Converting schema from {request.source_database_type}")
        
        # Convert database type string to enum
        try:
            db_type = DatabaseType(request.source_database_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {request.source_database_type}")
        
        # Convert DDL
        converted_ddl = schema_converter.convert_ddl(
            request.source_ddl,
            db_type,
            request.target_schema
        )
        
        # Validate converted schema
        validation_result = await schema_converter.validate_converted_schema(converted_ddl)
        
        # Save converted schema
        filename = f"{request.source_database_type}_converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        save_path = await schema_converter.save_converted_schema(converted_ddl, filename)
        
        return {
            "converted_ddl": converted_ddl,
            "validation_result": validation_result,
            "save_path": save_path,
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting schema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema conversion failed: {str(e)}")

@app.post("/migration/validate-connection")
async def validate_connection(
    source_system: str,
    connection_params: Dict[str, str],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Validate connection to source database"""
    try:
        logger.info(f"Validating connection to {source_system}")
        
        if source_system.lower() == "teradata":
            # Test Teradata connection
            conn_str = f"DRIVER={{Teradata}};DBCNAME={connection_params['host']};UID={connection_params['user']};PWD={connection_params['password']}"
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result:
                    return {"status": "success", "message": "Connection successful"}
                else:
                    return {"status": "failed", "message": "Connection test failed"}
                    
        elif source_system.lower() == "netezza":
            # Test Netezza connection
            conn_str = f"DRIVER={{NetezzaSQL}};SERVER={connection_params['host']};UID={connection_params['user']};PWD={connection_params['password']};DATABASE={connection_params['database']}"
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result:
                    return {"status": "success", "message": "Connection successful"}
                else:
                    return {"status": "failed", "message": "Connection test failed"}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source system: {source_system}")
            
    except Exception as e:
        logger.error(f"Connection validation failed: {str(e)}")
        return {"status": "failed", "message": f"Connection failed: {str(e)}"}

@app.get("/migration/supported-systems")
async def get_supported_systems() -> Dict[str, List[str]]:
    """Get list of supported source and target systems"""
    return {
        "source_systems": ["teradata", "netezza", "oracle", "mysql", "postgresql"],
        "target_systems": ["Azure SQL Database", "Azure Synapse Analytics", "Azure Data Lake"],
        "supported_operations": [
            "schema_analysis",
            "data_migration",
            "schema_conversion",
            "connection_validation"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)