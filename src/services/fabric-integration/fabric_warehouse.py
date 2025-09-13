"""
Fabric Data Warehouse Service
Handles integration with Microsoft Fabric Data Warehouse
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.sql.models import Database, Sku, CreateMode

from ...shared.config.settings import config_manager

class WarehouseStatus(Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    SCALING = "Scaling"
    PAUSED = "Paused"
    CREATING = "Creating"
    DELETING = "Deleting"

@dataclass
class WarehouseInfo:
    name: str
    status: WarehouseStatus
    compute_tier: str
    max_size_gb: int
    current_size_gb: float
    created_at: datetime
    last_accessed: datetime
    connection_string: str

@dataclass
class QueryResult:
    query_id: str
    status: str
    execution_time_ms: int
    rows_returned: int
    data: List[Dict[str, Any]]
    error_message: Optional[str] = None

class FabricWarehouseService:
    """Microsoft Fabric Data Warehouse integration service"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        
        # Azure credentials
        self.credential = DefaultAzureCredential()
        
        # Fabric configuration
        self.fabric_config = {
            'workspace_id': self.config.fabric_workspace_id,
            'capacity_id': self.config.fabric_capacity_id,
            'region': self.config.fabric_region
        }
        
        # Initialize SQL management client
        self.sql_client = SqlManagementClient(
            self.credential,
            self.config.subscription_id
        )
    
    async def create_warehouse(self, name: str, compute_tier: str = "Serverless",
                              max_size_gb: int = 100) -> WarehouseInfo:
        """Create a new Fabric Data Warehouse"""
        try:
            self.logger.info(f"Creating Fabric Data Warehouse: {name}")
            
            # In a real implementation, this would create a Fabric warehouse
            # For now, we'll create a mock warehouse info
            warehouse_info = WarehouseInfo(
                name=name,
                status=WarehouseStatus.CREATING,
                compute_tier=compute_tier,
                max_size_gb=max_size_gb,
                current_size_gb=0.0,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                connection_string=f"Server=tcp:{name}.database.windows.net,1433;Database={name};Authentication=Active Directory Default;"
            )
            
            # Simulate warehouse creation
            await asyncio.sleep(2)  # Simulate creation time
            warehouse_info.status = WarehouseStatus.ONLINE
            
            self.logger.info(f"Fabric Data Warehouse '{name}' created successfully")
            return warehouse_info
            
        except Exception as e:
            self.logger.error(f"Error creating warehouse: {str(e)}")
            raise
    
    async def get_warehouse_info(self, name: str) -> Optional[WarehouseInfo]:
        """Get information about a Fabric Data Warehouse"""
        try:
            self.logger.info(f"Getting warehouse info for: {name}")
            
            # In a real implementation, this would query the Fabric API
            # For now, we'll return mock data
            warehouse_info = WarehouseInfo(
                name=name,
                status=WarehouseStatus.ONLINE,
                compute_tier="Serverless",
                max_size_gb=100,
                current_size_gb=25.5,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                connection_string=f"Server=tcp:{name}.database.windows.net,1433;Database={name};Authentication=Active Directory Default;"
            )
            
            return warehouse_info
            
        except Exception as e:
            self.logger.error(f"Error getting warehouse info: {str(e)}")
            return None
    
    async def execute_sql_query(self, warehouse_name: str, query: str) -> QueryResult:
        """Execute a SQL query on the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Executing SQL query on warehouse: {warehouse_name}")
            
            query_id = f"query_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            start_time = datetime.now()
            
            # In a real implementation, this would execute the query on the warehouse
            # For now, we'll simulate query execution
            await asyncio.sleep(1)  # Simulate query execution time
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Mock query result
            mock_data = [
                {"id": 1, "name": "Sample Data", "value": 100},
                {"id": 2, "name": "Test Data", "value": 200},
                {"id": 3, "name": "Demo Data", "value": 300}
            ]
            
            result = QueryResult(
                query_id=query_id,
                status="completed",
                execution_time_ms=int(execution_time),
                rows_returned=len(mock_data),
                data=mock_data
            )
            
            self.logger.info(f"Query executed successfully: {query_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing SQL query: {str(e)}")
            return QueryResult(
                query_id=query_id if 'query_id' in locals() else "unknown",
                status="failed",
                execution_time_ms=0,
                rows_returned=0,
                data=[],
                error_message=str(e)
            )
    
    async def create_table(self, warehouse_name: str, table_name: str, 
                          schema: Dict[str, str], primary_key: str = None) -> Dict[str, Any]:
        """Create a table in the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Creating table '{table_name}' in warehouse '{warehouse_name}'")
            
            # Build CREATE TABLE statement
            columns = []
            for col_name, col_type in schema.items():
                columns.append(f"[{col_name}] {col_type}")
            
            create_table_sql = f"CREATE TABLE [{table_name}] (\n"
            create_table_sql += ",\n".join([f"    {col}" for col in columns])
            
            if primary_key:
                create_table_sql += f",\n    PRIMARY KEY ([{primary_key}])"
            
            create_table_sql += "\n);"
            
            # Execute the CREATE TABLE statement
            result = await self.execute_sql_query(warehouse_name, create_table_sql)
            
            if result.status == "completed":
                return {
                    "table_name": table_name,
                    "warehouse": warehouse_name,
                    "schema": schema,
                    "status": "created",
                    "sql": create_table_sql
                }
            else:
                raise Exception(f"Failed to create table: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"Error creating table: {str(e)}")
            raise
    
    async def insert_data(self, warehouse_name: str, table_name: str, 
                         data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert data into a table in the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Inserting {len(data)} rows into table '{table_name}'")
            
            if not data:
                return {"status": "skipped", "rows_inserted": 0}
            
            # Get column names from first row
            columns = list(data[0].keys())
            
            # Build INSERT statement
            insert_sql = f"INSERT INTO [{table_name}] ({', '.join([f'[{col}]' for col in columns])}) VALUES "
            
            # Build VALUES clause
            values_list = []
            for row in data:
                values = []
                for col in columns:
                    value = row.get(col)
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, str):
                        values.append(f"'{value.replace("'", "''")}'")
                    else:
                        values.append(str(value))
                values_list.append(f"({', '.join(values)})")
            
            insert_sql += ", ".join(values_list)
            
            # Execute the INSERT statement
            result = await self.execute_sql_query(warehouse_name, insert_sql)
            
            if result.status == "completed":
                return {
                    "table_name": table_name,
                    "warehouse": warehouse_name,
                    "rows_inserted": len(data),
                    "status": "completed"
                }
            else:
                raise Exception(f"Failed to insert data: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"Error inserting data: {str(e)}")
            raise
    
    async def query_table(self, warehouse_name: str, table_name: str, 
                         where_clause: str = None, limit: int = None) -> QueryResult:
        """Query a table in the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Querying table '{table_name}' in warehouse '{warehouse_name}'")
            
            # Build SELECT statement
            query = f"SELECT * FROM [{table_name}]"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            if limit:
                query += f" ORDER BY 1 OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
            
            # Execute the query
            result = await self.execute_sql_query(warehouse_name, query)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error querying table: {str(e)}")
            raise
    
    async def create_view(self, warehouse_name: str, view_name: str, 
                         view_definition: str) -> Dict[str, Any]:
        """Create a view in the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Creating view '{view_name}' in warehouse '{warehouse_name}'")
            
            # Build CREATE VIEW statement
            create_view_sql = f"CREATE VIEW [{view_name}] AS {view_definition}"
            
            # Execute the CREATE VIEW statement
            result = await self.execute_sql_query(warehouse_name, create_view_sql)
            
            if result.status == "completed":
                return {
                    "view_name": view_name,
                    "warehouse": warehouse_name,
                    "definition": view_definition,
                    "status": "created"
                }
            else:
                raise Exception(f"Failed to create view: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"Error creating view: {str(e)}")
            raise
    
    async def create_stored_procedure(self, warehouse_name: str, proc_name: str, 
                                    proc_definition: str) -> Dict[str, Any]:
        """Create a stored procedure in the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Creating stored procedure '{proc_name}' in warehouse '{warehouse_name}'")
            
            # Build CREATE PROCEDURE statement
            create_proc_sql = f"CREATE PROCEDURE [{proc_name}] AS {proc_definition}"
            
            # Execute the CREATE PROCEDURE statement
            result = await self.execute_sql_query(warehouse_name, create_proc_sql)
            
            if result.status == "completed":
                return {
                    "procedure_name": proc_name,
                    "warehouse": warehouse_name,
                    "definition": proc_definition,
                    "status": "created"
                }
            else:
                raise Exception(f"Failed to create stored procedure: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"Error creating stored procedure: {str(e)}")
            raise
    
    async def get_warehouse_metrics(self, warehouse_name: str) -> Dict[str, Any]:
        """Get performance metrics for the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Getting metrics for warehouse: {warehouse_name}")
            
            # In a real implementation, this would query actual metrics
            # For now, we'll return mock metrics
            metrics = {
                "warehouse_name": warehouse_name,
                "timestamp": datetime.now().isoformat(),
                "compute_utilization_percent": 45.2,
                "storage_used_gb": 25.5,
                "storage_available_gb": 74.5,
                "queries_executed_last_hour": 150,
                "average_query_duration_ms": 250.5,
                "active_connections": 12,
                "max_connections": 100,
                "cpu_utilization_percent": 35.8,
                "memory_utilization_percent": 42.1
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting warehouse metrics: {str(e)}")
            raise
    
    async def pause_warehouse(self, warehouse_name: str) -> Dict[str, Any]:
        """Pause the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Pausing warehouse: {warehouse_name}")
            
            # In a real implementation, this would pause the warehouse
            # For now, we'll simulate the operation
            await asyncio.sleep(2)  # Simulate pause time
            
            return {
                "warehouse_name": warehouse_name,
                "status": "paused",
                "paused_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error pausing warehouse: {str(e)}")
            raise
    
    async def resume_warehouse(self, warehouse_name: str) -> Dict[str, Any]:
        """Resume the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Resuming warehouse: {warehouse_name}")
            
            # In a real implementation, this would resume the warehouse
            # For now, we'll simulate the operation
            await asyncio.sleep(2)  # Simulate resume time
            
            return {
                "warehouse_name": warehouse_name,
                "status": "online",
                "resumed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error resuming warehouse: {str(e)}")
            raise
    
    async def delete_warehouse(self, warehouse_name: str) -> Dict[str, Any]:
        """Delete the Fabric Data Warehouse"""
        try:
            self.logger.info(f"Deleting warehouse: {warehouse_name}")
            
            # In a real implementation, this would delete the warehouse
            # For now, we'll simulate the operation
            await asyncio.sleep(3)  # Simulate deletion time
            
            return {
                "warehouse_name": warehouse_name,
                "status": "deleted",
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error deleting warehouse: {str(e)}")
            raise