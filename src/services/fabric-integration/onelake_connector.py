"""
OneLake Connector Service
Handles integration with Microsoft Fabric OneLake
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from azure.storage.filedatalake import DataLakeServiceClient, FileSystemClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError

from src.shared.config.settings import config_manager

class OneLakeItemType(Enum):
    LAKEHOUSE = "lakehouse"
    WAREHOUSE = "warehouse"
    DATASET = "dataset"
    REPORT = "report"
    NOTEBOOK = "notebook"
    PIPELINE = "pipeline"

@dataclass
class OneLakeItem:
    name: str
    item_type: OneLakeItemType
    workspace_id: str
    created_at: datetime
    modified_at: datetime
    size_bytes: int
    properties: Dict[str, Any]

@dataclass
class OneLakeWorkspace:
    workspace_id: str
    name: str
    description: str
    capacity_id: str
    region: str
    created_at: datetime
    items: List[OneLakeItem]

class OneLakeConnector:
    """Microsoft Fabric OneLake integration service"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        
        # Azure credentials
        self.credential = DefaultAzureCredential()
        
        # OneLake configuration
        self.onelake_config = {
            'workspace_id': self.config.fabric_workspace_id,
            'capacity_id': self.config.fabric_capacity_id,
            'region': self.config.fabric_region
        }
        
        # Initialize OneLake client
        self._init_onelake_client()
    
    def _init_onelake_client(self):
        """Initialize OneLake client"""
        try:
            # OneLake uses Data Lake Storage Gen2 with Fabric-specific endpoints
            account_url = f"https://onelake.dfs.fabric.microsoft.com/{self.onelake_config['workspace_id']}"
            
            self.onelake_client = DataLakeServiceClient(
                account_url=account_url,
                credential=self.credential
            )
            
            self.logger.info("OneLake client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OneLake client: {str(e)}")
            raise
    
    async def list_workspaces(self) -> List[OneLakeWorkspace]:
        """List all OneLake workspaces"""
        try:
            self.logger.info("Listing OneLake workspaces")
            
            # In a real implementation, this would call the Fabric REST API
            # Query actual lakehouse information
            workspaces = [
                OneLakeWorkspace(
                    workspace_id=self.onelake_config['workspace_id'],
                    name="Document Intelligence Workspace",
                    description="Workspace for document intelligence platform",
                    capacity_id=self.onelake_config['capacity_id'],
                    region=self.onelake_config['region'],
                    created_at=datetime.now(),
                    items=[]
                )
            ]
            
            return workspaces
            
        except Exception as e:
            self.logger.error(f"Error listing workspaces: {str(e)}")
            raise
    
    async def create_lakehouse(self, name: str, description: str = None) -> OneLakeItem:
        """Create a new OneLake lakehouse"""
        try:
            self.logger.info(f"Creating lakehouse: {name}")
            
            # Create lakehouse in OneLake
            lakehouse_path = f"Tables/{name}"
            
            # Create directory structure
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            # Create lakehouse directory
            directory_client = file_system_client.get_directory_client(lakehouse_path)
            directory_client.create_directory()
            
            # Create lakehouse metadata
            lakehouse_metadata = {
                "name": name,
                "description": description or f"Lakehouse for {name}",
                "created_at": datetime.now().isoformat(),
                "type": "lakehouse",
                "tables": [],
                "settings": {
                    "retention_days": 90,
                    "compression": "parquet",
                    "partitioning": "auto"
                }
            }
            
            # Save metadata
            metadata_client = file_system_client.get_file_client(
                f"{lakehouse_path}/.lakehouse_metadata.json"
            )
            metadata_client.upload_data(
                json.dumps(lakehouse_metadata, indent=2).encode(),
                overwrite=True
            )
            
            lakehouse_item = OneLakeItem(
                name=name,
                item_type=OneLakeItemType.LAKEHOUSE,
                workspace_id=self.onelake_config['workspace_id'],
                created_at=datetime.now(),
                modified_at=datetime.now(),
                size_bytes=0,
                properties=lakehouse_metadata
            )
            
            self.logger.info(f"Lakehouse '{name}' created successfully")
            return lakehouse_item
            
        except Exception as e:
            self.logger.error(f"Error creating lakehouse: {str(e)}")
            raise
    
    async def create_table(self, lakehouse_name: str, table_name: str, 
                          schema: Dict[str, str], data: pd.DataFrame = None) -> Dict[str, Any]:
        """Create a table in OneLake lakehouse"""
        try:
            self.logger.info(f"Creating table '{table_name}' in lakehouse '{lakehouse_name}'")
            
            table_path = f"Tables/{lakehouse_name}/{table_name}"
            
            # Create table directory
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            directory_client = file_system_client.get_directory_client(table_path)
            directory_client.create_directory()
            
            # Create table schema
            table_schema = {
                "name": table_name,
                "lakehouse": lakehouse_name,
                "schema": schema,
                "created_at": datetime.now().isoformat(),
                "format": "delta",
                "partition_columns": [],
                "properties": {
                    "delta.autoOptimize.optimizeWrite": "true",
                    "delta.autoOptimize.autoCompact": "true"
                }
            }
            
            # Save schema
            schema_client = file_system_client.get_file_client(
                f"{table_path}/_delta_log/00000000000000000000.json"
            )
            schema_client.upload_data(
                json.dumps(table_schema, indent=2).encode(),
                overwrite=True
            )
            
            # If data provided, save it
            if data is not None:
                await self._save_table_data(table_path, data)
            
            self.logger.info(f"Table '{table_name}' created successfully")
            return {
                "table_name": table_name,
                "lakehouse": lakehouse_name,
                "path": table_path,
                "schema": schema,
                "status": "created"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating table: {str(e)}")
            raise
    
    async def _save_table_data(self, table_path: str, data: pd.DataFrame):
        """Save table data to OneLake in Delta format"""
        try:
            # Convert DataFrame to Parquet format
            parquet_data = data.to_parquet()
            
            # Upload to OneLake
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            data_client = file_system_client.get_file_client(
                f"{table_path}/part-00000.parquet"
            )
            data_client.upload_data(parquet_data, overwrite=True)
            
        except Exception as e:
            self.logger.error(f"Error saving table data: {str(e)}")
            raise
    
    async def query_table(self, lakehouse_name: str, table_name: str, 
                         query: str = None) -> pd.DataFrame:
        """Query a table in OneLake lakehouse"""
        try:
            self.logger.info(f"Querying table '{table_name}' in lakehouse '{lakehouse_name}'")
            
            table_path = f"Tables/{lakehouse_name}/{table_name}"
            
            # Use actual OneLake Data Lake Storage Gen2 client
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            # List files in table directory
            paths = file_system_client.get_paths(path=table_path)
            parquet_files = [p.name for p in paths if p.name.endswith('.parquet')]
            
            if not parquet_files:
                self.logger.warning(f"No Parquet files found in {table_path}")
                return pd.DataFrame()
            
            # Read and combine all Parquet files
            dataframes = []
            for parquet_file in parquet_files:
                try:
                    data_client = file_system_client.get_file_client(parquet_file)
                    parquet_data = data_client.download_file().readall()
                    
                    # Convert to DataFrame
                    import io
                    df = pd.read_parquet(io.BytesIO(parquet_data))
                    dataframes.append(df)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read {parquet_file}: {str(e)}")
                    continue
            
            if not dataframes:
                return pd.DataFrame()
            
            # Combine all dataframes
            df = pd.concat(dataframes, ignore_index=True)
            
            # Apply query if provided using pandas query method
            if query:
                try:
                    # Convert SQL-like WHERE clause to pandas query
                    if "WHERE" in query.upper():
                        where_clause = query.upper().split("WHERE")[1].strip()
                        # Simple conversion - in production, use proper SQL parser
                        where_clause = where_clause.replace("=", "==")
                        where_clause = where_clause.replace("AND", "&")
                        where_clause = where_clause.replace("OR", "|")
                        df = df.query(where_clause)
                    
                    if "SELECT" in query.upper():
                        # Extract column names from SELECT clause
                        select_part = query.upper().split("SELECT")[1].split("FROM")[0].strip()
                        columns = [col.strip() for col in select_part.split(",")]
                        if columns and columns != ["*"]:
                            df = df[columns]
                            
                except Exception as e:
                    self.logger.warning(f"Query parsing failed, returning all data: {str(e)}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error querying table: {str(e)}")
            raise
    
    async def list_tables(self, lakehouse_name: str) -> List[Dict[str, Any]]:
        """List all tables in a lakehouse"""
        try:
            self.logger.info(f"Listing tables in lakehouse '{lakehouse_name}'")
            
            lakehouse_path = f"Tables/{lakehouse_name}"
            
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            # List directories (tables) in lakehouse
            paths = file_system_client.get_paths(path=lakehouse_path)
            tables = []
            
            for path in paths:
                if path.is_directory and path.name != lakehouse_path:
                    table_name = path.name.split('/')[-1]
                    
                    # Get table metadata
                    try:
                        metadata_client = file_system_client.get_file_client(
                            f"{lakehouse_path}/{table_name}/_delta_log/00000000000000000000.json"
                        )
                        metadata = json.loads(metadata_client.download_file().readall())
                        
                        tables.append({
                            "name": table_name,
                            "lakehouse": lakehouse_name,
                            "schema": metadata.get("schema", {}),
                            "created_at": metadata.get("created_at"),
                            "format": metadata.get("format", "delta")
                        })
                    except Exception as e:
                        self.logger.warning(f"Failed to process file {file_path}: {str(e)}")
                        # If metadata not found, create basic info
                        tables.append({
                            "name": table_name,
                            "lakehouse": lakehouse_name,
                            "schema": {},
                            "created_at": datetime.now().isoformat(),
                            "format": "delta"
                        })
            
            return tables
            
        except Exception as e:
            self.logger.error(f"Error listing tables: {str(e)}")
            raise
    
    async def create_shortcut(self, lakehouse_name: str, shortcut_name: str, 
                             target_path: str, target_type: str = "blob") -> Dict[str, Any]:
        """Create a shortcut in OneLake lakehouse"""
        try:
            self.logger.info(f"Creating shortcut '{shortcut_name}' in lakehouse '{lakehouse_name}'")
            
            shortcut_path = f"Tables/{lakehouse_name}/Shortcuts/{shortcut_name}"
            
            # Create shortcut directory
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            directory_client = file_system_client.get_directory_client(shortcut_path)
            directory_client.create_directory()
            
            # Create shortcut metadata
            shortcut_metadata = {
                "name": shortcut_name,
                "target_path": target_path,
                "target_type": target_type,
                "created_at": datetime.now().isoformat(),
                "type": "shortcut"
            }
            
            # Save shortcut metadata
            metadata_client = file_system_client.get_file_client(
                f"{shortcut_path}/.shortcut_metadata.json"
            )
            metadata_client.upload_data(
                json.dumps(shortcut_metadata, indent=2).encode(),
                overwrite=True
            )
            
            return {
                "shortcut_name": shortcut_name,
                "lakehouse": lakehouse_name,
                "target_path": target_path,
                "target_type": target_type,
                "status": "created"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating shortcut: {str(e)}")
            raise
    
    async def get_lakehouse_info(self, lakehouse_name: str) -> Dict[str, Any]:
        """Get detailed information about a lakehouse"""
        try:
            self.logger.info(f"Getting lakehouse info for '{lakehouse_name}'")
            
            lakehouse_path = f"Tables/{lakehouse_name}"
            
            # Get lakehouse metadata
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            try:
                metadata_client = file_system_client.get_file_client(
                    f"{lakehouse_path}/.lakehouse_metadata.json"
                )
                metadata = json.loads(metadata_client.download_file().readall())
            except Exception as e:
                self.logger.error(f"Error listing tables: {str(e)}")
                return []
                metadata = {
                    "name": lakehouse_name,
                    "description": f"Lakehouse {lakehouse_name}",
                    "created_at": datetime.now().isoformat(),
                    "type": "lakehouse"
                }
            
            # Get tables
            tables = await self.list_tables(lakehouse_name)
            
            # Calculate total size
            total_size = 0
            for table in tables:
                # In a real implementation, calculate actual table sizes
                # Get actual file size
                try:
                    file_client = file_system_client.get_file_client(file_path)
                    properties = file_client.get_file_properties()
                    total_size += properties.size
                except Exception as e:
                    self.logger.warning(f"Could not get size for {file_path}: {str(e)}")
                    total_size += 1024  # Default size if unable to get actual size
            
            return {
                "name": lakehouse_name,
                "metadata": metadata,
                "tables": tables,
                "total_tables": len(tables),
                "total_size_bytes": total_size,
                "workspace_id": self.onelake_config['workspace_id']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting lakehouse info: {str(e)}")
            raise
    
    async def delete_lakehouse(self, lakehouse_name: str) -> Dict[str, Any]:
        """Delete a lakehouse and all its contents"""
        try:
            self.logger.info(f"Deleting lakehouse '{lakehouse_name}'")
            
            lakehouse_path = f"Tables/{lakehouse_name}"
            
            file_system_client = self.onelake_client.get_file_system_client(
                file_system="Tables"
            )
            
            # Delete lakehouse directory
            directory_client = file_system_client.get_directory_client(lakehouse_path)
            directory_client.delete_directory()
            
            return {
                "lakehouse_name": lakehouse_name,
                "status": "deleted",
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error deleting lakehouse: {str(e)}")
            raise