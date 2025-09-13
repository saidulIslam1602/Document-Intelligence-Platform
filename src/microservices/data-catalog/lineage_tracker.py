"""
Data Lineage Tracking Service
Comprehensive data lineage tracking and metadata management
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import networkx as nx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from ...shared.config.settings import config_manager
from ...shared.storage.sql_service import SQLService
from ...shared.cache.redis_cache import cache_service

class DataAssetType(Enum):
    """Types of data assets"""
    TABLE = "table"
    VIEW = "view"
    FILE = "file"
    API = "api"
    STREAM = "stream"
    MODEL = "model"

class LineageType(Enum):
    """Types of data lineage relationships"""
    DIRECT = "direct"
    TRANSFORMED = "transformed"
    AGGREGATED = "aggregated"
    FILTERED = "filtered"
    JOINED = "joined"
    COPIED = "copied"

@dataclass
class DataAsset:
    """Data asset metadata"""
    asset_id: str
    name: str
    asset_type: DataAssetType
    description: str
    location: str
    schema: Dict[str, Any]
    owner: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = None
    quality_score: float = 0.0
    last_accessed: Optional[datetime] = None

@dataclass
class LineageRelationship:
    """Data lineage relationship"""
    relationship_id: str
    source_asset_id: str
    target_asset_id: str
    lineage_type: LineageType
    transformation_description: str
    created_at: datetime
    metadata: Dict[str, Any] = None

@dataclass
class DataFlow:
    """Data flow between assets"""
    flow_id: str
    source_asset: DataAsset
    target_asset: DataAsset
    relationships: List[LineageRelationship]
    flow_metadata: Dict[str, Any]

class DataLineageTracker:
    """Advanced data lineage tracking and metadata management"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage for lineage graph
        self.lineage_graph = nx.DiGraph()
        self.assets = {}
        self.relationships = {}
        
        # Initialize with existing data
        asyncio.create_task(self._initialize_lineage())
    
    async def _initialize_lineage(self):
        """Initialize lineage tracking with existing data"""
        try:
            # Register existing tables
            await self._register_existing_tables()
            
            # Build initial lineage relationships
            await self._build_initial_lineage()
            
            self.logger.info("Data lineage tracking initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing lineage tracking: {str(e)}")
    
    async def _register_existing_tables(self):
        """Register existing database tables as data assets"""
        try:
            # Get list of tables
            tables_query = """
                SELECT 
                    t.TABLE_NAME,
                    t.TABLE_TYPE,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.IS_NULLABLE,
                    c.COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.TABLES t
                LEFT JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
                WHERE t.TABLE_TYPE = 'BASE TABLE'
                ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION
            """
            
            results = self.sql_service.execute_query(tables_query)
            
            # Group by table
            table_schemas = {}
            for row in results:
                table_name = row['TABLE_NAME']
                if table_name not in table_schemas:
                    table_schemas[table_name] = {
                        'columns': [],
                        'table_type': row['TABLE_TYPE']
                    }
                
                if row['COLUMN_NAME']:
                    table_schemas[table_name]['columns'].append({
                        'name': row['COLUMN_NAME'],
                        'type': row['DATA_TYPE'],
                        'nullable': row['IS_NULLABLE'] == 'YES',
                        'default': row['COLUMN_DEFAULT']
                    })
            
            # Register each table as a data asset
            for table_name, schema in table_schemas.items():
                asset_id = f"table_{table_name}"
                asset = DataAsset(
                    asset_id=asset_id,
                    name=table_name,
                    asset_type=DataAssetType.TABLE,
                    description=f"Database table: {table_name}",
                    location=f"sql://{self.config.sql_server_name}/{self.config.sql_database_name}/{table_name}",
                    schema=schema,
                    owner="system",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    tags=["database", "sql", "structured"]
                )
                
                await self.register_asset(asset)
                
        except Exception as e:
            self.logger.error(f"Error registering existing tables: {str(e)}")
    
    async def _build_initial_lineage(self):
        """Build initial lineage relationships based on foreign keys"""
        try:
            # Get foreign key relationships
            fk_query = """
                SELECT 
                    fk.TABLE_NAME as source_table,
                    fk.COLUMN_NAME as source_column,
                    pk.TABLE_NAME as target_table,
                    pk.COLUMN_NAME as target_column,
                    fk.CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk ON rc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk ON rc.UNIQUE_CONSTRAINT_NAME = pk.CONSTRAINT_NAME
            """
            
            results = self.sql_service.execute_query(fk_query)
            
            for row in results:
                source_asset_id = f"table_{row['source_table']}"
                target_asset_id = f"table_{row['target_table']}"
                
                if source_asset_id in self.assets and target_asset_id in self.assets:
                    relationship = LineageRelationship(
                        relationship_id=f"fk_{row['CONSTRAINT_NAME']}",
                        source_asset_id=source_asset_id,
                        target_asset_id=target_asset_id,
                        lineage_type=LineageType.DIRECT,
                        transformation_description=f"Foreign key relationship: {row['source_column']} -> {row['target_column']}",
                        created_at=datetime.utcnow(),
                        metadata={
                            "source_column": row['source_column'],
                            "target_column": row['target_column'],
                            "constraint_name": row['CONSTRAINT_NAME']
                        }
                    )
                    
                    await self.add_lineage_relationship(relationship)
                    
        except Exception as e:
            self.logger.error(f"Error building initial lineage: {str(e)}")
    
    async def register_asset(self, asset: DataAsset) -> str:
        """Register a new data asset"""
        try:
            self.assets[asset.asset_id] = asset
            self.lineage_graph.add_node(asset.asset_id, **asdict(asset))
            
            # Store in database
            await self._store_asset_metadata(asset)
            
            self.logger.info(f"Registered data asset: {asset.asset_id}")
            return asset.asset_id
            
        except Exception as e:
            self.logger.error(f"Error registering asset: {str(e)}")
            raise
    
    async def add_lineage_relationship(self, relationship: LineageRelationship) -> str:
        """Add a lineage relationship between assets"""
        try:
            if relationship.source_asset_id not in self.assets:
                raise ValueError(f"Source asset {relationship.source_asset_id} not found")
            if relationship.target_asset_id not in self.assets:
                raise ValueError(f"Target asset {relationship.target_asset_id} not found")
            
            self.relationships[relationship.relationship_id] = relationship
            self.lineage_graph.add_edge(
                relationship.source_asset_id,
                relationship.target_asset_id,
                **asdict(relationship)
            )
            
            # Store in database
            await self._store_lineage_relationship(relationship)
            
            self.logger.info(f"Added lineage relationship: {relationship.relationship_id}")
            return relationship.relationship_id
            
        except Exception as e:
            self.logger.error(f"Error adding lineage relationship: {str(e)}")
            raise
    
    async def get_asset_lineage(self, asset_id: str, direction: str = "both") -> Dict[str, Any]:
        """Get lineage information for a specific asset"""
        try:
            if asset_id not in self.assets:
                raise ValueError(f"Asset {asset_id} not found")
            
            asset = self.assets[asset_id]
            
            # Get upstream lineage (sources)
            upstream_assets = []
            if direction in ["upstream", "both"]:
                for source_id in self.lineage_graph.predecessors(asset_id):
                    upstream_assets.append(self.assets[source_id])
            
            # Get downstream lineage (targets)
            downstream_assets = []
            if direction in ["downstream", "both"]:
                for target_id in self.lineage_graph.successors(asset_id):
                    downstream_assets.append(self.assets[target_id])
            
            # Get relationships
            relationships = []
            for rel_id, rel in self.relationships.items():
                if rel.source_asset_id == asset_id or rel.target_asset_id == asset_id:
                    relationships.append(rel)
            
            return {
                "asset": asdict(asset),
                "upstream_assets": [asdict(a) for a in upstream_assets],
                "downstream_assets": [asdict(a) for a in downstream_assets],
                "relationships": [asdict(r) for r in relationships],
                "lineage_depth": self._calculate_lineage_depth(asset_id),
                "impact_score": self._calculate_impact_score(asset_id)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting asset lineage: {str(e)}")
            raise
    
    async def get_data_flow(self, source_asset_id: str, target_asset_id: str) -> Optional[DataFlow]:
        """Get data flow between two assets"""
        try:
            if source_asset_id not in self.assets or target_asset_id not in self.assets:
                return None
            
            # Check if there's a path between the assets
            if not nx.has_path(self.lineage_graph, source_asset_id, target_asset_id):
                return None
            
            # Get the shortest path
            path = nx.shortest_path(self.lineage_graph, source_asset_id, target_asset_id)
            
            # Get relationships along the path
            relationships = []
            for i in range(len(path) - 1):
                source = path[i]
                target = path[i + 1]
                
                # Find relationship between these nodes
                for rel_id, rel in self.relationships.items():
                    if rel.source_asset_id == source and rel.target_asset_id == target:
                        relationships.append(rel)
                        break
            
            return DataFlow(
                flow_id=f"flow_{source_asset_id}_{target_asset_id}",
                source_asset=self.assets[source_asset_id],
                target_asset=self.assets[target_asset_id],
                relationships=relationships,
                flow_metadata={
                    "path_length": len(path) - 1,
                    "path": path
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting data flow: {str(e)}")
            return None
    
    async def search_assets(self, query: str, asset_type: Optional[DataAssetType] = None) -> List[DataAsset]:
        """Search for data assets"""
        try:
            results = []
            query_lower = query.lower()
            
            for asset in self.assets.values():
                # Filter by type if specified
                if asset_type and asset.asset_type != asset_type:
                    continue
                
                # Search in name, description, and tags
                if (query_lower in asset.name.lower() or
                    query_lower in asset.description.lower() or
                    any(query_lower in tag.lower() for tag in asset.tags or [])):
                    results.append(asset)
            
            # Sort by relevance (name matches first, then description, then tags)
            results.sort(key=lambda x: (
                query_lower not in x.name.lower(),
                query_lower not in x.description.lower(),
                not any(query_lower in tag.lower() for tag in x.tags or [])
            ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching assets: {str(e)}")
            raise
    
    async def get_impact_analysis(self, asset_id: str) -> Dict[str, Any]:
        """Get impact analysis for an asset (what would be affected if it changed)"""
        try:
            if asset_id not in self.assets:
                raise ValueError(f"Asset {asset_id} not found")
            
            # Get all downstream assets (transitive closure)
            downstream_assets = set()
            for target_id in nx.descendants(self.lineage_graph, asset_id):
                downstream_assets.add(target_id)
            
            # Get all upstream assets (transitive closure)
            upstream_assets = set()
            for source_id in nx.ancestors(self.lineage_graph, asset_id):
                upstream_assets.add(source_id)
            
            # Calculate impact metrics
            total_downstream = len(downstream_assets)
            total_upstream = len(upstream_assets)
            
            # Get critical paths (longest paths to/from this asset)
            critical_downstream_paths = []
            critical_upstream_paths = []
            
            for target_id in downstream_assets:
                try:
                    path = nx.shortest_path(self.lineage_graph, asset_id, target_id)
                    critical_downstream_paths.append(path)
                except nx.NetworkXNoPath:
                    pass
            
            for source_id in upstream_assets:
                try:
                    path = nx.shortest_path(self.lineage_graph, source_id, asset_id)
                    critical_upstream_paths.append(path)
                except nx.NetworkXNoPath:
                    pass
            
            return {
                "asset_id": asset_id,
                "impact_metrics": {
                    "total_downstream_assets": total_downstream,
                    "total_upstream_assets": total_upstream,
                    "max_downstream_depth": max(len(path) - 1 for path in critical_downstream_paths) if critical_downstream_paths else 0,
                    "max_upstream_depth": max(len(path) - 1 for path in critical_upstream_paths) if critical_upstream_paths else 0,
                    "total_impact_score": total_downstream + total_upstream
                },
                "downstream_assets": [asdict(self.assets[aid]) for aid in downstream_assets],
                "upstream_assets": [asdict(self.assets[aid]) for aid in upstream_assets],
                "critical_paths": {
                    "downstream": critical_downstream_paths,
                    "upstream": critical_upstream_paths
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting impact analysis: {str(e)}")
            raise
    
    def _calculate_lineage_depth(self, asset_id: str) -> int:
        """Calculate the maximum depth of lineage for an asset"""
        try:
            # Get maximum depth in both directions
            max_downstream = 0
            max_upstream = 0
            
            # Downstream depth
            for target_id in nx.descendants(self.lineage_graph, asset_id):
                try:
                    path_length = nx.shortest_path_length(self.lineage_graph, asset_id, target_id)
                    max_downstream = max(max_downstream, path_length)
                except nx.NetworkXNoPath:
                    pass
            
            # Upstream depth
            for source_id in nx.ancestors(self.lineage_graph, asset_id):
                try:
                    path_length = nx.shortest_path_length(self.lineage_graph, source_id, asset_id)
                    max_upstream = max(max_upstream, path_length)
                except nx.NetworkXNoPath:
                    pass
            
            return max(max_downstream, max_upstream)
            
        except Exception as e:
            self.logger.error(f"Error calculating lineage depth: {str(e)}")
            return 0
    
    def _calculate_impact_score(self, asset_id: str) -> float:
        """Calculate impact score for an asset"""
        try:
            # Count downstream and upstream assets
            downstream_count = len(list(nx.descendants(self.lineage_graph, asset_id)))
            upstream_count = len(list(nx.ancestors(self.lineage_graph, asset_id)))
            
            # Calculate score (0-1 scale)
            total_assets = len(self.assets)
            if total_assets == 0:
                return 0.0
            
            impact_score = (downstream_count + upstream_count) / total_assets
            return min(impact_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating impact score: {str(e)}")
            return 0.0
    
    async def _store_asset_metadata(self, asset: DataAsset):
        """Store asset metadata in database"""
        try:
            # This would store asset metadata in a database table
            # For now, just log
            self.logger.info(f"Stored asset metadata: {asset.asset_id}")
        except Exception as e:
            self.logger.error(f"Error storing asset metadata: {str(e)}")
    
    async def _store_lineage_relationship(self, relationship: LineageRelationship):
        """Store lineage relationship in database"""
        try:
            # This would store lineage relationship in a database table
            # For now, just log
            self.logger.info(f"Stored lineage relationship: {relationship.relationship_id}")
        except Exception as e:
            self.logger.error(f"Error storing lineage relationship: {str(e)}")

# Pydantic models for API
class AssetRegistrationRequest(BaseModel):
    name: str
    asset_type: str
    description: str
    location: str
    schema: Dict[str, Any]
    owner: str
    tags: List[str] = []

class LineageRelationshipRequest(BaseModel):
    source_asset_id: str
    target_asset_id: str
    lineage_type: str
    transformation_description: str
    metadata: Dict[str, Any] = {}

class AssetSearchRequest(BaseModel):
    query: str
    asset_type: Optional[str] = None

# Global lineage tracker instance
lineage_tracker = DataLineageTracker()