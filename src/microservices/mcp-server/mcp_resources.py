"""
MCP Resources Manager
Implements MCP-compliant resources for exposing platform data
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class MCPResourceManager:
    """Manager for MCP resources that expose platform data"""
    
    def __init__(self, service_endpoints: Dict[str, str]):
        self.service_endpoints = service_endpoints
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """Get list of available MCP resources"""
        return [
            {
                "uri": "document://{document_id}",
                "name": "Document Resource",
                "description": "Access document data including metadata, content, and processing results",
                "mimeType": "application/json"
            },
            {
                "uri": "analytics://metrics/{time_range}",
                "name": "Analytics Metrics Resource",
                "description": "Access real-time analytics metrics for specified time range",
                "mimeType": "application/json"
            },
            {
                "uri": "automation://score/{time_range}",
                "name": "Automation Score Resource",
                "description": "Access automation scoring data to track progress toward 90%+ goal",
                "mimeType": "application/json"
            },
            {
                "uri": "invoice://{document_id}",
                "name": "Invoice Resource",
                "description": "Access extracted invoice data with validation status",
                "mimeType": "application/json"
            },
            {
                "uri": "fine-tuning://job/{job_id}",
                "name": "Fine-Tuning Job Resource",
                "description": "Access fine-tuning job status and metrics",
                "mimeType": "application/json"
            },
            {
                "uri": "quality://validation/{document_id}",
                "name": "Quality Validation Resource",
                "description": "Access data quality validation results",
                "mimeType": "application/json"
            },
            {
                "uri": "search://index/{index_name}",
                "name": "Search Index Resource",
                "description": "Access search index configuration and statistics",
                "mimeType": "application/json"
            }
        ]
    
    async def read_resource(
        self,
        resource_uri: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Read a resource by URI"""
        # Parse the resource URI
        uri_parts = resource_uri.split("://")
        if len(uri_parts) != 2:
            raise ValueError(f"Invalid resource URI: {resource_uri}")
        
        resource_type = uri_parts[0]
        resource_path = uri_parts[1]
        
        # Route to appropriate handler
        if resource_type == "document":
            return await self._read_document_resource(resource_path, parameters)
        elif resource_type == "analytics":
            return await self._read_analytics_resource(resource_path, parameters)
        elif resource_type == "automation":
            return await self._read_automation_resource(resource_path, parameters)
        elif resource_type == "invoice":
            return await self._read_invoice_resource(resource_path, parameters)
        elif resource_type == "fine-tuning":
            return await self._read_fine_tuning_resource(resource_path, parameters)
        elif resource_type == "quality":
            return await self._read_quality_resource(resource_path, parameters)
        elif resource_type == "search":
            return await self._read_search_resource(resource_path, parameters)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")
    
    async def _read_document_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read document resource"""
        try:
            document_id = resource_path.strip("/")
            
            # Call Document Ingestion Service to get document
            doc_ingestion_url = self.service_endpoints.get("document-ingestion")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{doc_ingestion_url}/documents/{document_id}"
                )
                
                if response.status_code == 200:
                    document = response.json()
                    return {
                        "resource_type": "document",
                        "document_id": document_id,
                        "data": document,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Document not found: {document_id}")
        
        except Exception as e:
            logger.error(f"Error reading document resource: {str(e)}")
            raise
    
    async def _read_analytics_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read analytics metrics resource"""
        try:
            # Parse path: metrics/{time_range}
            path_parts = resource_path.split("/")
            if len(path_parts) >= 2 and path_parts[0] == "metrics":
                time_range = path_parts[1]
            else:
                time_range = "24h"
            
            # Call Analytics Service to get metrics
            analytics_url = self.service_endpoints.get("analytics")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{analytics_url}/analytics/realtime",
                    params={"time_range": time_range}
                )
                
                if response.status_code == 200:
                    metrics = response.json()
                    return {
                        "resource_type": "analytics_metrics",
                        "time_range": time_range,
                        "data": metrics,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to get analytics metrics: {response.text}")
        
        except Exception as e:
            logger.error(f"Error reading analytics resource: {str(e)}")
            raise
    
    async def _read_automation_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read automation score resource"""
        try:
            # Parse path: score/{time_range}
            path_parts = resource_path.split("/")
            if len(path_parts) >= 2 and path_parts[0] == "score":
                time_range = path_parts[1]
            else:
                time_range = "24h"
            
            # Call Analytics Service to get automation metrics
            analytics_url = self.service_endpoints.get("analytics")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{analytics_url}/analytics/automation-metrics",
                    params={"time_range": time_range}
                )
                
                if response.status_code == 200:
                    automation_data = response.json()
                    return {
                        "resource_type": "automation_score",
                        "time_range": time_range,
                        "data": automation_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to get automation metrics: {response.text}")
        
        except Exception as e:
            logger.error(f"Error reading automation resource: {str(e)}")
            raise
    
    async def _read_invoice_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read invoice resource"""
        try:
            document_id = resource_path.strip("/")
            
            # Call AI Processing Service to get invoice data
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get document first
                doc_response = await client.get(
                    f"{self.service_endpoints.get('document-ingestion')}/documents/{document_id}"
                )
                
                if doc_response.status_code != 200:
                    raise Exception(f"Document not found: {document_id}")
                
                document = doc_response.json()
                
                # Process to get invoice data if not already processed
                if "invoice_data" not in document.get("processing_result", {}):
                    process_response = await client.post(
                        f"{ai_processing_url}/process",
                        json={
                            "document_id": document_id,
                            "user_id": "system",
                            "processing_options": {"extract_invoice": True}
                        }
                    )
                    
                    if process_response.status_code == 200:
                        document = process_response.json()
                
                return {
                    "resource_type": "invoice",
                    "document_id": document_id,
                    "data": document.get("processing_result", {}).get("invoice_data", {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error reading invoice resource: {str(e)}")
            raise
    
    async def _read_fine_tuning_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read fine-tuning job resource"""
        try:
            # Parse path: job/{job_id}
            path_parts = resource_path.split("/")
            if len(path_parts) >= 2 and path_parts[0] == "job":
                job_id = path_parts[1]
            else:
                raise ValueError("Invalid fine-tuning resource path")
            
            # Call AI Processing Service to get fine-tuning job status
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{ai_processing_url}/fine-tuning/jobs/{job_id}"
                )
                
                if response.status_code == 200:
                    job_data = response.json()
                    return {
                        "resource_type": "fine_tuning_job",
                        "job_id": job_id,
                        "data": job_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Fine-tuning job not found: {job_id}")
        
        except Exception as e:
            logger.error(f"Error reading fine-tuning resource: {str(e)}")
            raise
    
    async def _read_quality_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read quality validation resource"""
        try:
            # Parse path: validation/{document_id}
            path_parts = resource_path.split("/")
            if len(path_parts) >= 2 and path_parts[0] == "validation":
                document_id = path_parts[1]
            else:
                raise ValueError("Invalid quality resource path")
            
            # Call Data Quality Service to get validation results
            data_quality_url = self.service_endpoints.get("data-quality")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{data_quality_url}/validation/{document_id}"
                )
                
                if response.status_code == 200:
                    validation_data = response.json()
                    return {
                        "resource_type": "quality_validation",
                        "document_id": document_id,
                        "data": validation_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Validation data not found: {document_id}")
        
        except Exception as e:
            logger.error(f"Error reading quality resource: {str(e)}")
            raise
    
    async def _read_search_resource(
        self,
        resource_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read search index resource"""
        try:
            # Parse path: index/{index_name}
            path_parts = resource_path.split("/")
            if len(path_parts) >= 2 and path_parts[0] == "index":
                index_name = path_parts[1]
            else:
                index_name = "documents"
            
            # Call AI Chat Service to get search index info
            ai_chat_url = self.service_endpoints.get("ai-chat")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{ai_chat_url}/search/index/{index_name}"
                )
                
                if response.status_code == 200:
                    index_data = response.json()
                    return {
                        "resource_type": "search_index",
                        "index_name": index_name,
                        "data": index_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Search index not found: {index_name}")
        
        except Exception as e:
            logger.error(f"Error reading search resource: {str(e)}")
            raise

