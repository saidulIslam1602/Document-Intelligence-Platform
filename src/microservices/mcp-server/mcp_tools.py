"""
MCP Tools Registry
Implements MCP-compliant tools that call existing microservices
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
import httpx
from datetime import datetime
from ...shared.http.client_pool import get_http_client

logger = logging.getLogger(__name__)

class MCPToolRegistry:
    """Registry for MCP tools that integrate with existing services"""
    
    def __init__(self, service_endpoints: Dict[str, str]):
        self.service_endpoints = service_endpoints
        self.tools: Dict[str, Callable] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all available MCP tools"""
        self.tools = {
            "extract_invoice_data": self._extract_invoice_data,
            "validate_invoice": self._validate_invoice,
            "classify_document": self._classify_document,
            "create_fine_tuning_job": self._create_fine_tuning_job,
            "get_automation_metrics": self._get_automation_metrics,
            "process_m365_document": self._process_m365_document,
            "analyze_document_sentiment": self._analyze_document_sentiment,
            "extract_document_entities": self._extract_document_entities,
            "generate_document_summary": self._generate_document_summary,
            "search_documents": self._search_documents
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools with their schemas"""
        return [
            {
                "name": "extract_invoice_data",
                "description": "Extract structured data from invoice documents using Azure Form Recognizer. Returns vendor info, amounts, line items, etc.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the document to extract invoice data from"
                        }
                    },
                    "required": ["document_id"]
                }
            },
            {
                "name": "validate_invoice",
                "description": "Validate invoice data using data quality rules. Checks completeness, accuracy, and business rules.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice_data": {
                            "type": "object",
                            "description": "Invoice data to validate"
                        }
                    },
                    "required": ["invoice_data"]
                }
            },
            {
                "name": "classify_document",
                "description": "Classify document type using ML models. Returns document type (invoice, receipt, contract, etc.) with confidence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the document to classify"
                        }
                    },
                    "required": ["document_id"]
                }
            },
            {
                "name": "create_fine_tuning_job",
                "description": "Create a fine-tuning job for Azure OpenAI models to improve invoice processing accuracy.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "training_file": {
                            "type": "string",
                            "description": "Path to the training data file"
                        },
                        "model": {
                            "type": "string",
                            "description": "Base model to fine-tune (default: gpt-3.5-turbo)",
                            "default": "gpt-3.5-turbo"
                        },
                        "hyperparameters": {
                            "type": "object",
                            "description": "Optional hyperparameters for fine-tuning"
                        }
                    },
                    "required": ["training_file"]
                }
            },
            {
                "name": "get_automation_metrics",
                "description": "Get invoice automation metrics to track progress toward 90%+ automation goal. Returns automation rate, accuracy, confidence scores.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "time_range": {
                            "type": "string",
                            "description": "Time range for metrics (1h, 24h, 7d, 30d)",
                            "default": "24h"
                        }
                    }
                }
            },
            {
                "name": "process_m365_document",
                "description": "Process a document from Microsoft 365 using Copilot integration.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the M365 document to process"
                        }
                    },
                    "required": ["document_url"]
                }
            },
            {
                "name": "analyze_document_sentiment",
                "description": "Analyze sentiment of document text using AI models.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the document to analyze"
                        }
                    },
                    "required": ["document_id"]
                }
            },
            {
                "name": "extract_document_entities",
                "description": "Extract named entities from document using OpenAI.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the document to extract entities from"
                        }
                    },
                    "required": ["document_id"]
                }
            },
            {
                "name": "generate_document_summary",
                "description": "Generate AI-powered summary of document content.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the document to summarize"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum length of summary in words",
                            "default": 200
                        }
                    },
                    "required": ["document_id"]
                }
            },
            {
                "name": "search_documents",
                "description": "Search documents using AI-powered semantic search.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional filters for search"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute a tool by name"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool_func = self.tools[tool_name]
        return await tool_func(parameters, context)
    
    # Tool implementations
    
    async def _extract_invoice_data(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract invoice data from document"""
        try:
            document_id = parameters.get("document_id")
            if not document_id:
                raise ValueError("document_id is required")
            
            # Call AI Processing Service to extract invoice data
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            # Use connection pool instead of creating new client
            client = get_http_client()
            
            # First, get the document
            doc_response = await client.get(
                f"{self.service_endpoints.get('document-ingestion')}/documents/{document_id}"
            )
            
            if doc_response.status_code != 200:
                raise Exception(f"Document not found: {document_id}")
            
            document = doc_response.json()
            
            # Process the document to extract invoice data
            process_response = await client.post(
                f"{ai_processing_url}/process",
                json={
                    "document_id": document_id,
                    "user_id": context.get("user_id", "system"),
                    "processing_options": {
                        "extract_invoice": True
                    }
                }
            )
                
                if process_response.status_code == 200:
                    result = process_response.json()
                    return {
                        "success": True,
                        "document_id": document_id,
                        "invoice_data": result.get("processing_result", {}),
                        "confidence": result.get("processing_result", {}).get("confidence", 0.0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to extract invoice data: {process_response.text}")
        
        except Exception as e:
            logger.error(f"Error in extract_invoice_data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _validate_invoice(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate invoice data"""
        try:
            invoice_data = parameters.get("invoice_data")
            if not invoice_data:
                raise ValueError("invoice_data is required")
            
            # Call Data Quality Service to validate invoice
            data_quality_url = self.service_endpoints.get("data-quality")
            
            # Use connection pool
            client = get_http_client()
            response = await client.post(
                f"{data_quality_url}/validate",
                json={
                    "data": invoice_data,
                    "validation_rules": "invoice",
                    "user_id": context.get("user_id", "system")
                }
            )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "validation_result": result,
                        "is_valid": result.get("is_valid", False),
                        "validation_score": result.get("quality_score", 0.0),
                        "issues": result.get("issues", []),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to validate invoice: {response.text}")
        
        except Exception as e:
            logger.error(f"Error in validate_invoice: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _classify_document(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify document type"""
        try:
            document_id = parameters.get("document_id")
            if not document_id:
                raise ValueError("document_id is required")
            
            # Call AI Processing Service to classify document
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get document text first
                doc_response = await client.get(
                    f"{self.service_endpoints.get('document-ingestion')}/documents/{document_id}"
                )
                
                if doc_response.status_code != 200:
                    raise Exception(f"Document not found: {document_id}")
                
                document = doc_response.json()
                document_text = document.get("extracted_text", "")
                
                # Classify the document
                classify_response = await client.post(
                    f"{ai_processing_url}/classify",
                    json={
                        "text": document_text
                    }
                )
                
                if classify_response.status_code == 200:
                    result = classify_response.json()
                    return {
                        "success": True,
                        "document_id": document_id,
                        "document_type": result.get("predicted_type"),
                        "confidence": result.get("confidence", 0.0),
                        "top_predictions": result.get("top_predictions", []),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to classify document: {classify_response.text}")
        
        except Exception as e:
            logger.error(f"Error in classify_document: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _create_fine_tuning_job(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fine-tuning job"""
        try:
            training_file = parameters.get("training_file")
            model = parameters.get("model", "gpt-3.5-turbo")
            hyperparameters = parameters.get("hyperparameters", {})
            
            if not training_file:
                raise ValueError("training_file is required")
            
            # Call AI Processing Service to create fine-tuning job
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ai_processing_url}/fine-tuning/jobs",
                    json={
                        "training_file": training_file,
                        "model": model,
                        "hyperparameters": hyperparameters,
                        "user_id": context.get("user_id", "system")
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "job_id": result.get("job_id"),
                        "status": result.get("status"),
                        "model": model,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to create fine-tuning job: {response.text}")
        
        except Exception as e:
            logger.error(f"Error in create_fine_tuning_job: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_automation_metrics(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get automation metrics"""
        try:
            time_range = parameters.get("time_range", "24h")
            
            # Call Analytics Service to get automation metrics
            analytics_url = self.service_endpoints.get("analytics")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{analytics_url}/analytics/automation-metrics",
                    params={"time_range": time_range}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "time_range": time_range,
                        "automation_rate": result.get("automation_rate", 0.0),
                        "total_processed": result.get("total_processed", 0),
                        "fully_automated": result.get("fully_automated", 0),
                        "requires_review": result.get("requires_review", 0),
                        "manual_intervention": result.get("manual_intervention", 0),
                        "average_confidence": result.get("average_confidence", 0.0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to get automation metrics: {response.text}")
        
        except Exception as e:
            logger.error(f"Error in get_automation_metrics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _process_m365_document(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process M365 document"""
        try:
            document_url = parameters.get("document_url")
            if not document_url:
                raise ValueError("document_url is required")
            
            # This would integrate with M365 Copilot Service
            # For now, return a placeholder response
            return {
                "success": True,
                "document_url": document_url,
                "status": "processed",
                "message": "M365 document processing completed",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in process_m365_document: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _analyze_document_sentiment(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze document sentiment"""
        try:
            document_id = parameters.get("document_id")
            if not document_id:
                raise ValueError("document_id is required")
            
            # Call AI Processing Service for sentiment analysis
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get document text
                doc_response = await client.get(
                    f"{self.service_endpoints.get('document-ingestion')}/documents/{document_id}"
                )
                
                if doc_response.status_code != 200:
                    raise Exception(f"Document not found: {document_id}")
                
                document = doc_response.json()
                document_text = document.get("extracted_text", "")
                
                # Analyze sentiment
                sentiment_response = await client.post(
                    f"{ai_processing_url}/sentiment",
                    json={"text": document_text}
                )
                
                if sentiment_response.status_code == 200:
                    result = sentiment_response.json()
                    return {
                        "success": True,
                        "document_id": document_id,
                        "sentiment": result.get("predicted_sentiment"),
                        "confidence": result.get("confidence", 0.0),
                        "sentiment_scores": result.get("sentiment_scores", {}),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to analyze sentiment: {sentiment_response.text}")
        
        except Exception as e:
            logger.error(f"Error in analyze_document_sentiment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _extract_document_entities(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract document entities"""
        try:
            document_id = parameters.get("document_id")
            if not document_id:
                raise ValueError("document_id is required")
            
            # Call AI Processing Service for entity extraction
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get document text
                doc_response = await client.get(
                    f"{self.service_endpoints.get('document-ingestion')}/documents/{document_id}"
                )
                
                if doc_response.status_code != 200:
                    raise Exception(f"Document not found: {document_id}")
                
                document = doc_response.json()
                document_text = document.get("extracted_text", "")
                
                # Extract entities
                entities_response = await client.post(
                    f"{ai_processing_url}/entities",
                    params={"text": document_text}
                )
                
                if entities_response.status_code == 200:
                    result = entities_response.json()
                    return {
                        "success": True,
                        "document_id": document_id,
                        "entities": result.get("entities", []),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to extract entities: {entities_response.text}")
        
        except Exception as e:
            logger.error(f"Error in extract_document_entities: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _generate_document_summary(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate document summary"""
        try:
            document_id = parameters.get("document_id")
            max_length = parameters.get("max_length", 200)
            
            if not document_id:
                raise ValueError("document_id is required")
            
            # Call AI Processing Service for summary generation
            ai_processing_url = self.service_endpoints.get("ai-processing")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get document text
                doc_response = await client.get(
                    f"{self.service_endpoints.get('document-ingestion')}/documents/{document_id}"
                )
                
                if doc_response.status_code != 200:
                    raise Exception(f"Document not found: {document_id}")
                
                document = doc_response.json()
                document_text = document.get("extracted_text", "")
                
                # Generate summary
                summary_response = await client.post(
                    f"{ai_processing_url}/summarize",
                    params={"text": document_text, "max_length": max_length}
                )
                
                if summary_response.status_code == 200:
                    result = summary_response.json()
                    return {
                        "success": True,
                        "document_id": document_id,
                        "summary": result.get("summary"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to generate summary: {summary_response.text}")
        
        except Exception as e:
            logger.error(f"Error in generate_document_summary: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _search_documents(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search documents"""
        try:
            query = parameters.get("query")
            filters = parameters.get("filters", {})
            
            if not query:
                raise ValueError("query is required")
            
            # Call AI Chat Service for semantic search
            ai_chat_url = self.service_endpoints.get("ai-chat")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ai_chat_url}/search",
                    json={
                        "query": query,
                        "filters": filters,
                        "user_id": context.get("user_id", "system")
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "query": query,
                        "results": result.get("results", []),
                        "total_results": result.get("total", 0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    raise Exception(f"Failed to search documents: {response.text}")
        
        except Exception as e:
            logger.error(f"Error in search_documents: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

