"""
Data Catalog Service
REST API for data discovery, lineage tracking, and metadata management
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .lineage_tracker import (
    lineage_tracker, AssetRegistrationRequest, LineageRelationshipRequest, 
    AssetSearchRequest, DataAssetType, LineageType
)
from src.shared.config.settings import config_manager
from src.shared.storage.sql_service import SQLService
from src.shared.cache.redis_cache import cache_service, cache_result

# Initialize FastAPI app
app = FastAPI(
    title="Data Catalog Service",
    description="Data discovery, lineage tracking, and metadata management",
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
config = config_manager.get_azure_config()
sql_service = SQLService(config.sql_connection_string)
logger = logging.getLogger(__name__)

# Pydantic models
class AssetResponse(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    description: str
    location: str
    schema: Dict[str, Any]
    owner: str
    created_at: str
    updated_at: str
    tags: List[str]
    quality_score: float
    last_accessed: Optional[str] = None

class LineageResponse(BaseModel):
    asset: AssetResponse
    upstream_assets: List[AssetResponse]
    downstream_assets: List[AssetResponse]
    relationships: List[Dict[str, Any]]
    lineage_depth: int
    impact_score: float

class SearchResponse(BaseModel):
    query: str
    total_results: int
    assets: List[AssetResponse]
    search_time_ms: float

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "data-catalog"
    }

# Asset management endpoints
@app.post("/assets", response_model=AssetResponse)
async def register_asset(request: AssetRegistrationRequest):
    """Register a new data asset"""
    try:
        from .lineage_tracker import DataAsset
        
        # Create asset object
        asset = DataAsset(
            asset_id=f"{request.asset_type}_{request.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            name=request.name,
            asset_type=DataAssetType(request.asset_type),
            description=request.description,
            location=request.location,
            schema=request.schema,
            owner=request.owner,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=request.tags
        )
        
        # Register asset
        asset_id = await lineage_tracker.register_asset(asset)
        
        # Return response
        return AssetResponse(
            asset_id=asset.asset_id,
            name=asset.name,
            asset_type=asset.asset_type.value,
            description=asset.description,
            location=asset.location,
            schema=asset.schema,
            owner=asset.owner,
            created_at=asset.created_at.isoformat(),
            updated_at=asset.updated_at.isoformat(),
            tags=asset.tags or [],
            quality_score=asset.quality_score,
            last_accessed=asset.last_accessed.isoformat() if asset.last_accessed else None
        )
        
    except Exception as e:
        logger.error(f"Error registering asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to register asset")

@app.get("/assets", response_model=List[AssetResponse])
@cache_result(ttl=300, key_prefix="all_assets")  # Cache for 5 minutes
async def list_assets(
    asset_type: Optional[str] = None,
    owner: Optional[str] = None,
    limit: int = 100
):
    """List all data assets with optional filtering"""
    try:
        assets = list(lineage_tracker.assets.values())
        
        # Filter by asset type
        if asset_type:
            assets = [a for a in assets if a.asset_type.value == asset_type]
        
        # Filter by owner
        if owner:
            assets = [a for a in assets if a.owner == owner]
        
        # Limit results
        assets = assets[:limit]
        
        # Convert to response format
        return [
            AssetResponse(
                asset_id=asset.asset_id,
                name=asset.name,
                asset_type=asset.asset_type.value,
                description=asset.description,
                location=asset.location,
                schema=asset.schema,
                owner=asset.owner,
                created_at=asset.created_at.isoformat(),
                updated_at=asset.updated_at.isoformat(),
                tags=asset.tags or [],
                quality_score=asset.quality_score,
                last_accessed=asset.last_accessed.isoformat() if asset.last_accessed else None
            )
            for asset in assets
        ]
        
    except Exception as e:
        logger.error(f"Error listing assets: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list assets")

@app.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str):
    """Get a specific data asset"""
    try:
        if asset_id not in lineage_tracker.assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = lineage_tracker.assets[asset_id]
        
        return AssetResponse(
            asset_id=asset.asset_id,
            name=asset.name,
            asset_type=asset.asset_type.value,
            description=asset.description,
            location=asset.location,
            schema=asset.schema,
            owner=asset.owner,
            created_at=asset.created_at.isoformat(),
            updated_at=asset.updated_at.isoformat(),
            tags=asset.tags or [],
            quality_score=asset.quality_score,
            last_accessed=asset.last_accessed.isoformat() if asset.last_accessed else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get asset")

# Lineage tracking endpoints
@app.post("/lineage/relationships")
async def add_lineage_relationship(request: LineageRelationshipRequest):
    """Add a lineage relationship between assets"""
    try:
        from .lineage_tracker import LineageRelationship
        
        # Create relationship object
        relationship = LineageRelationship(
            relationship_id=f"rel_{request.source_asset_id}_{request.target_asset_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            source_asset_id=request.source_asset_id,
            target_asset_id=request.target_asset_id,
            lineage_type=LineageType(request.lineage_type),
            transformation_description=request.transformation_description,
            created_at=datetime.utcnow(),
            metadata=request.metadata
        )
        
        # Add relationship
        relationship_id = await lineage_tracker.add_lineage_relationship(relationship)
        
        return {
            "message": "Lineage relationship added successfully",
            "relationship_id": relationship_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error adding lineage relationship: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add lineage relationship")

@app.get("/lineage/{asset_id}", response_model=LineageResponse)
@cache_result(ttl=60, key_prefix="lineage")  # Cache for 1 minute
async def get_asset_lineage(asset_id: str, direction: str = "both"):
    """Get lineage information for a specific asset"""
    try:
        lineage_data = await lineage_tracker.get_asset_lineage(asset_id, direction)
        
        # Convert to response format
        return LineageResponse(
            asset=AssetResponse(
                asset_id=lineage_data["asset"]["asset_id"],
                name=lineage_data["asset"]["name"],
                asset_type=lineage_data["asset"]["asset_type"],
                description=lineage_data["asset"]["description"],
                location=lineage_data["asset"]["location"],
                schema=lineage_data["asset"]["schema"],
                owner=lineage_data["asset"]["owner"],
                created_at=lineage_data["asset"]["created_at"],
                updated_at=lineage_data["asset"]["updated_at"],
                tags=lineage_data["asset"]["tags"] or [],
                quality_score=lineage_data["asset"]["quality_score"],
                last_accessed=lineage_data["asset"]["last_accessed"]
            ),
            upstream_assets=[
                AssetResponse(
                    asset_id=asset["asset_id"],
                    name=asset["name"],
                    asset_type=asset["asset_type"],
                    description=asset["description"],
                    location=asset["location"],
                    schema=asset["schema"],
                    owner=asset["owner"],
                    created_at=asset["created_at"],
                    updated_at=asset["updated_at"],
                    tags=asset["tags"] or [],
                    quality_score=asset["quality_score"],
                    last_accessed=asset["last_accessed"]
                )
                for asset in lineage_data["upstream_assets"]
            ],
            downstream_assets=[
                AssetResponse(
                    asset_id=asset["asset_id"],
                    name=asset["name"],
                    asset_type=asset["asset_type"],
                    description=asset["description"],
                    location=asset["location"],
                    schema=asset["schema"],
                    owner=asset["owner"],
                    created_at=asset["created_at"],
                    updated_at=asset["updated_at"],
                    tags=asset["tags"] or [],
                    quality_score=asset["quality_score"],
                    last_accessed=asset["last_accessed"]
                )
                for asset in lineage_data["downstream_assets"]
            ],
            relationships=lineage_data["relationships"],
            lineage_depth=lineage_data["lineage_depth"],
            impact_score=lineage_data["impact_score"]
        )
        
    except Exception as e:
        logger.error(f"Error getting asset lineage: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get asset lineage")

@app.get("/lineage/flow/{source_asset_id}/{target_asset_id}")
async def get_data_flow(source_asset_id: str, target_asset_id: str):
    """Get data flow between two assets"""
    try:
        flow = await lineage_tracker.get_data_flow(source_asset_id, target_asset_id)
        
        if not flow:
            raise HTTPException(status_code=404, detail="No data flow found between assets")
        
        return {
            "flow_id": flow.flow_id,
            "source_asset": {
                "asset_id": flow.source_asset.asset_id,
                "name": flow.source_asset.name,
                "asset_type": flow.source_asset.asset_type.value
            },
            "target_asset": {
                "asset_id": flow.target_asset.asset_id,
                "name": flow.target_asset.name,
                "asset_type": flow.target_asset.asset_type.value
            },
            "relationships": [
                {
                    "relationship_id": rel.relationship_id,
                    "lineage_type": rel.lineage_type.value,
                    "transformation_description": rel.transformation_description,
                    "metadata": rel.metadata or {}
                }
                for rel in flow.relationships
            ],
            "flow_metadata": flow.flow_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data flow: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get data flow")

# Search endpoints
@app.post("/search", response_model=SearchResponse)
async def search_assets(request: AssetSearchRequest):
    """Search for data assets"""
    try:
        start_time = datetime.utcnow()
        
        # Perform search
        asset_type = DataAssetType(request.asset_type) if request.asset_type else None
        results = await lineage_tracker.search_assets(request.query, asset_type)
        
        end_time = datetime.utcnow()
        search_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Convert to response format
        assets = [
            AssetResponse(
                asset_id=asset.asset_id,
                name=asset.name,
                asset_type=asset.asset_type.value,
                description=asset.description,
                location=asset.location,
                schema=asset.schema,
                owner=asset.owner,
                created_at=asset.created_at.isoformat(),
                updated_at=asset.updated_at.isoformat(),
                tags=asset.tags or [],
                quality_score=asset.quality_score,
                last_accessed=asset.last_accessed.isoformat() if asset.last_accessed else None
            )
            for asset in results
        ]
        
        return SearchResponse(
            query=request.query,
            total_results=len(assets),
            assets=assets,
            search_time_ms=round(search_time_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"Error searching assets: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search assets")

# Impact analysis endpoints
@app.get("/impact/{asset_id}")
async def get_impact_analysis(asset_id: str):
    """Get impact analysis for an asset"""
    try:
        impact_data = await lineage_tracker.get_impact_analysis(asset_id)
        return impact_data
        
    except Exception as e:
        logger.error(f"Error getting impact analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get impact analysis")

# Dashboard endpoints
@app.get("/dashboard/overview")
@cache_result(ttl=60, key_prefix="catalog_dashboard")  # Cache for 1 minute
async def get_catalog_dashboard():
    """Get data catalog dashboard overview"""
    try:
        assets = list(lineage_tracker.assets.values())
        relationships = list(lineage_tracker.relationships.values())
        
        # Calculate statistics
        total_assets = len(assets)
        total_relationships = len(relationships)
        
        # Group by asset type
        asset_types = {}
        for asset in assets:
            asset_type = asset.asset_type.value
            if asset_type not in asset_types:
                asset_types[asset_type] = 0
            asset_types[asset_type] += 1
        
        # Group by owner
        owners = {}
        for asset in assets:
            owner = asset.owner
            if owner not in owners:
                owners[owner] = 0
            owners[owner] += 1
        
        # Calculate average quality score
        avg_quality_score = sum(asset.quality_score for asset in assets) / len(assets) if assets else 0
        
        # Get recently updated assets
        recent_assets = sorted(assets, key=lambda x: x.updated_at, reverse=True)[:5]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_assets": total_assets,
                "total_relationships": total_relationships,
                "avg_quality_score": round(avg_quality_score, 3)
            },
            "asset_types": asset_types,
            "owners": owners,
            "recent_assets": [
                {
                    "asset_id": asset.asset_id,
                    "name": asset.name,
                    "asset_type": asset.asset_type.value,
                    "updated_at": asset.updated_at.isoformat()
                }
                for asset in recent_assets
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting catalog dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get catalog dashboard")

@app.get("/dashboard/lineage-graph")
async def get_lineage_graph():
    """Get lineage graph data for visualization"""
    try:
        # Get graph nodes and edges
        nodes = []
        edges = []
        
        # Add nodes
        for asset_id, asset in lineage_tracker.assets.items():
            nodes.append({
                "id": asset_id,
                "label": asset.name,
                "type": asset.asset_type.value,
                "owner": asset.owner,
                "quality_score": asset.quality_score
            })
        
        # Add edges
        for rel_id, rel in lineage_tracker.relationships.items():
            edges.append({
                "id": rel_id,
                "source": rel.source_asset_id,
                "target": rel.target_asset_id,
                "type": rel.lineage_type.value,
                "description": rel.transformation_description
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting lineage graph: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get lineage graph")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)