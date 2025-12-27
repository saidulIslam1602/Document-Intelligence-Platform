"""
Azure OpenAI Fine-Tuning Service
Implements Microsoft's recommended fine-tuning approach for document intelligence
"""

import asyncio
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from openai import AzureOpenAI
from azure.core.exceptions import AzureError

from src.shared.config.settings import config_manager
from src.shared.events.event_sourcing import DomainEvent, EventType, EventBus
from src.shared.storage.sql_service import SQLService

class FineTuningStatus(Enum):
    """Fine-tuning job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FineTuningMethod(Enum):
    """Fine-tuning method enumeration"""
    SUPERVISED = "supervised"
    DPO = "dpo"  # Direct Preference Optimization
    RFT = "rft"  # Reinforcement Fine Tuning

@dataclass
class FineTuningJob:
    """Fine-tuning job data structure"""
    job_id: str
    model_name: str
    training_file_id: str
    validation_file_id: Optional[str]
    status: FineTuningStatus
    created_at: datetime
    finished_at: Optional[datetime]
    fine_tuned_model: Optional[str]
    hyperparameters: Dict[str, Any]
    training_tokens: Optional[int]
    error_message: Optional[str]

@dataclass
class TrainingData:
    """Training data structure for fine-tuning"""
    messages: List[Dict[str, str]]
    document_type: str
    industry: str
    confidence_score: float
    metadata: Dict[str, Any]

class DocumentFineTuningService:
    """Azure OpenAI Fine-Tuning Service for Document Intelligence"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=self.config.openai_endpoint,
            api_key=self.config.openai_api_key,
            api_version="2024-08-01-preview"
        )
        
        # Initialize SQL service for data storage
        self.sql_service = SQLService(self.config.sql_connection_string)
        
        # Supported models for fine-tuning
        self.supported_models = {
            "gpt-4o": {
                "training_cost_per_1k_tokens": 0.003,
                "hosting_cost_per_hour": 3.0,
                "input_cost_per_1k_tokens": 0.005,
                "output_cost_per_1k_tokens": 0.015,
                "max_training_tokens": 65536,
                "max_inference_tokens": 128000
            },
            "gpt-4o-mini": {
                "training_cost_per_1k_tokens": 0.0033,
                "hosting_cost_per_hour": 1.7,
                "input_cost_per_1k_tokens": 0.00015,
                "output_cost_per_1k_tokens": 0.0006,
                "max_training_tokens": 65536,
                "max_inference_tokens": 128000
            },
            "gpt-3.5-turbo": {
                "training_cost_per_1k_tokens": 0.008,
                "hosting_cost_per_hour": 1.0,
                "input_cost_per_1k_tokens": 0.0015,
                "output_cost_per_1k_tokens": 0.002,
                "max_training_tokens": 16384,
                "max_inference_tokens": 16384
            }
        }
        
        # Document types for fine-tuning
        self.document_types = [
            'invoice', 'receipt', 'contract', 'report', 'correspondence',
            'technical', 'legal', 'medical', 'financial', 'insurance',
            'tax_document', 'business_card', 'id_document', 'other'
        ]
        
        # Industry-specific categories
        self.industries = [
            'financial_services', 'healthcare', 'manufacturing', 'retail',
            'education', 'government', 'technology', 'legal', 'insurance'
        ]
    
    async def prepare_training_data(
        self, 
        documents: List[Dict[str, Any]], 
        document_type: str,
        industry: str,
        min_samples: int = 50
    ) -> Tuple[str, str]:
        """Prepare training and validation data for fine-tuning"""
        try:
            self.logger.info(f"Preparing training data for {document_type} in {industry}")
            
            # Filter documents by type and industry
            filtered_docs = [
                doc for doc in documents 
                if doc.get('document_type') == document_type and doc.get('industry') == industry
            ]
            
            if len(filtered_docs) < min_samples:
                raise ValueError(f"Insufficient data: {len(filtered_docs)} samples, minimum {min_samples} required")
            
            # Prepare training examples
            training_examples = []
            validation_examples = []
            
            for i, doc in enumerate(filtered_docs):
                # Create training example in JSONL format
                example = self._create_training_example(doc, document_type, industry)
                
                # Split 80/20 for training/validation
                if i < len(filtered_docs) * 0.8:
                    training_examples.append(example)
                else:
                    validation_examples.append(example)
            
            # Save training data to JSONL files
            training_file_path = await self._save_jsonl_file(
                training_examples, 
                f"training_{document_type}_{industry}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
            
            validation_file_path = await self._save_jsonl_file(
                validation_examples,
                f"validation_{document_type}_{industry}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
            
            # Upload files to Azure OpenAI
            training_file_id = await self._upload_training_file(training_file_path)
            validation_file_id = await self._upload_training_file(validation_file_path)
            
            self.logger.info(f"Training data prepared: {len(training_examples)} training, {len(validation_examples)} validation")
            
            return training_file_id, validation_file_id
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {str(e)}")
            raise
    
    def _create_training_example(self, doc: Dict[str, Any], document_type: str, industry: str) -> Dict[str, Any]:
        """Create a training example in the required format"""
        
        # Extract document content
        content = doc.get('extracted_text', '')
        if not content:
            content = doc.get('summary', '')
        
        # Create system message based on document type and industry
        system_message = self._create_system_message(document_type, industry)
        
        # Create user message with document content
        user_message = f"Analyze this {document_type} document:\n\n{content[:2000]}..."  # Truncate for token limits
        
        # Create assistant response based on document analysis
        assistant_message = self._create_assistant_response(doc, document_type, industry)
        
        return {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]
        }
    
    def _create_system_message(self, document_type: str, industry: str) -> str:
        """Create system message for fine-tuning"""
        
        system_templates = {
            'invoice': f"You are an expert {industry} invoice analysis AI. Extract key information including vendor, amounts, dates, line items, and payment terms. Provide structured JSON output.",
            'contract': f"You are a specialized {industry} contract analysis AI. Identify parties, key terms, obligations, dates, and legal clauses. Provide detailed analysis in structured format.",
            'report': f"You are a {industry} report analysis AI. Extract key findings, metrics, recommendations, and executive summary. Provide comprehensive analysis.",
            'medical': f"You are a healthcare document analysis AI. Extract patient information, diagnoses, treatments, medications, and medical codes while maintaining HIPAA compliance.",
            'legal': f"You are a legal document analysis AI specializing in {industry}. Extract case details, legal precedents, statutes, and key legal arguments.",
            'financial': f"You are a financial document analysis AI for {industry}. Extract financial metrics, ratios, trends, and key performance indicators."
        }
        
        return system_templates.get(document_type, f"You are an expert {industry} document analysis AI. Extract key information and provide structured analysis.")
    
    def _create_assistant_response(self, doc: Dict[str, Any], document_type: str, industry: str) -> str:
        """Create assistant response for training"""
        
        # Extract key information from document
        entities = doc.get('entities', {})
        summary = doc.get('summary', '')
        confidence = doc.get('confidence', 0.0)
        
        # Create structured response based on document type
        response = {
            "document_type": document_type,
            "industry": industry,
            "confidence_score": confidence,
            "key_entities": entities,
            "summary": summary,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Add type-specific fields
        if document_type == 'invoice':
            response.update({
                "vendor": entities.get('organizations', [{}])[0].get('name', 'Unknown'),
                "total_amount": entities.get('amounts', [0])[0],
                "invoice_date": entities.get('dates', ['Unknown'])[0],
                "line_items": doc.get('line_items', [])
            })
        elif document_type == 'contract':
            response.update({
                "parties": entities.get('organizations', []),
                "contract_dates": entities.get('dates', []),
                "key_terms": doc.get('key_terms', []),
                "obligations": doc.get('obligations', [])
            })
        elif document_type == 'medical':
            response.update({
                "patient_info": entities.get('people', []),
                "diagnoses": doc.get('diagnoses', []),
                "medications": doc.get('medications', []),
                "procedures": doc.get('procedures', [])
            })
        
        return json.dumps(response, indent=2)
    
    async def _save_jsonl_file(self, examples: List[Dict[str, Any]], filename: str) -> str:
        """Save training examples to JSONL file"""
        try:
            file_path = f"training_data/{filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for example in examples:
                    f.write(json.dumps(example, ensure_ascii=False) + '\n')
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error saving JSONL file: {str(e)}")
            raise
    
    async def _upload_training_file(self, file_path: str) -> str:
        """Upload training file to Azure OpenAI"""
        try:
            with open(file_path, 'rb') as f:
                response = self.client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            
            self.logger.info(f"File uploaded successfully: {response.id}")
            return response.id
            
        except Exception as e:
            self.logger.error(f"Error uploading training file: {str(e)}")
            raise
    
    async def create_fine_tuning_job(
        self,
        model_name: str,
        training_file_id: str,
        validation_file_id: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        suffix: Optional[str] = None
    ) -> FineTuningJob:
        """Create a fine-tuning job"""
        try:
            if model_name not in self.supported_models:
                raise ValueError(f"Model {model_name} not supported for fine-tuning")
            
            # Set default hyperparameters
            default_hyperparameters = {
                "n_epochs": 3,
                "batch_size": 4,
                "learning_rate_multiplier": 0.1
            }
            
            if hyperparameters:
                default_hyperparameters.update(hyperparameters)
            
            # Create fine-tuning job
            job_params = {
                "model": model_name,
                "training_file": training_file_id,
                "hyperparameters": default_hyperparameters
            }
            
            if validation_file_id:
                job_params["validation_file"] = validation_file_id
            
            if suffix:
                job_params["suffix"] = suffix
            
            response = self.client.fine_tuning.jobs.create(**job_params)
            
            # Create job record
            job = FineTuningJob(
                job_id=response.id,
                model_name=model_name,
                training_file_id=training_file_id,
                validation_file_id=validation_file_id,
                status=FineTuningStatus(response.status),
                created_at=datetime.fromtimestamp(response.created_at),
                finished_at=datetime.fromtimestamp(response.finished_at) if response.finished_at else None,
                fine_tuned_model=response.fine_tuned_model,
                hyperparameters=default_hyperparameters,
                training_tokens=response.trained_tokens,
                error_message=response.error.message if response.error else None
            )
            
            # Store job in database
            await self._store_fine_tuning_job(job)
            
            # Publish event
            if self.event_bus:
                await self.event_bus.publish(DomainEvent(
                    event_type=EventType.AI_MODEL_TRAINED,
                    aggregate_id=job.job_id,
                    event_data={
                        "job_id": job.job_id,
                        "model_name": model_name,
                        "status": job.status.value,
                        "created_at": job.created_at.isoformat()
                    }
                ))
            
            self.logger.info(f"Fine-tuning job created: {job.job_id}")
            return job
            
        except Exception as e:
            self.logger.error(f"Error creating fine-tuning job: {str(e)}")
            raise
    
    async def get_fine_tuning_job(self, job_id: str) -> FineTuningJob:
        """Get fine-tuning job status"""
        try:
            response = self.client.fine_tuning.jobs.retrieve(job_id)
            
            job = FineTuningJob(
                job_id=response.id,
                model_name=response.model,
                training_file_id=response.training_file,
                validation_file_id=response.validation_file,
                status=FineTuningStatus(response.status),
                created_at=datetime.fromtimestamp(response.created_at),
                finished_at=datetime.fromtimestamp(response.finished_at) if response.finished_at else None,
                fine_tuned_model=response.fine_tuned_model,
                hyperparameters=response.hyperparameters.__dict__ if response.hyperparameters else {},
                training_tokens=response.trained_tokens,
                error_message=response.error.message if response.error else None
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error retrieving fine-tuning job: {str(e)}")
            raise
    
    async def list_fine_tuning_jobs(self, limit: int = 20) -> List[FineTuningJob]:
        """List all fine-tuning jobs"""
        try:
            response = self.client.fine_tuning.jobs.list(limit=limit)
            
            jobs = []
            for job_data in response.data:
                job = FineTuningJob(
                    job_id=job_data.id,
                    model_name=job_data.model,
                    training_file_id=job_data.training_file,
                    validation_file_id=job_data.validation_file,
                    status=FineTuningStatus(job_data.status),
                    created_at=datetime.fromtimestamp(job_data.created_at),
                    finished_at=datetime.fromtimestamp(job_data.finished_at) if job_data.finished_at else None,
                    fine_tuned_model=job_data.fine_tuned_model,
                    hyperparameters=job_data.hyperparameters.__dict__ if job_data.hyperparameters else {},
                    training_tokens=job_data.trained_tokens,
                    error_message=job_data.error.message if job_data.error else None
                )
                jobs.append(job)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error listing fine-tuning jobs: {str(e)}")
            raise
    
    async def cancel_fine_tuning_job(self, job_id: str) -> bool:
        """Cancel a fine-tuning job"""
        try:
            response = self.client.fine_tuning.jobs.cancel(job_id)
            
            if response.status == "cancelled":
                self.logger.info(f"Fine-tuning job cancelled: {job_id}")
                return True
            else:
                self.logger.warning(f"Failed to cancel job {job_id}: {response.status}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling fine-tuning job: {str(e)}")
            raise
    
    async def deploy_fine_tuned_model(
        self, 
        model_name: str, 
        deployment_name: str,
        deployment_type: str = "standard"
    ) -> str:
        """Deploy a fine-tuned model"""
        try:
            # Create deployment
            deployment = self.client.deployments.create(
                model=model_name,
                deployment_name=deployment_name,
                scale_settings={
                    "scale_type": deployment_type,
                    "capacity": 1
                }
            )
            
            self.logger.info(f"Model deployed: {deployment.id}")
            return deployment.id
            
        except Exception as e:
            self.logger.error(f"Error deploying model: {str(e)}")
            raise
    
    async def evaluate_fine_tuned_model(
        self, 
        model_name: str, 
        test_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate fine-tuned model performance"""
        try:
            results = {
                "model_name": model_name,
                "total_documents": len(test_documents),
                "correct_predictions": 0,
                "accuracy": 0.0,
                "average_confidence": 0.0,
                "document_type_accuracy": {},
                "industry_accuracy": {},
                "evaluation_timestamp": datetime.now().isoformat()
            }
            
            total_confidence = 0.0
            
            for doc in test_documents:
                # Test model prediction
                prediction = await self._test_model_prediction(model_name, doc)
                
                # Check if prediction is correct
                if prediction.get('document_type') == doc.get('document_type'):
                    results["correct_predictions"] += 1
                
                # Track confidence
                confidence = prediction.get('confidence_score', 0.0)
                total_confidence += confidence
                
                # Track by document type
                doc_type = doc.get('document_type', 'unknown')
                if doc_type not in results["document_type_accuracy"]:
                    results["document_type_accuracy"][doc_type] = {"correct": 0, "total": 0}
                
                results["document_type_accuracy"][doc_type]["total"] += 1
                if prediction.get('document_type') == doc_type:
                    results["document_type_accuracy"][doc_type]["correct"] += 1
                
                # Track by industry
                industry = doc.get('industry', 'unknown')
                if industry not in results["industry_accuracy"]:
                    results["industry_accuracy"][industry] = {"correct": 0, "total": 0}
                
                results["industry_accuracy"][industry]["total"] += 1
                if prediction.get('industry') == industry:
                    results["industry_accuracy"][industry]["correct"] += 1
            
            # Calculate final metrics
            results["accuracy"] = results["correct_predictions"] / results["total_documents"]
            results["average_confidence"] = total_confidence / results["total_documents"]
            
            # Calculate per-category accuracy
            for category in results["document_type_accuracy"]:
                data = results["document_type_accuracy"][category]
                data["accuracy"] = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            
            for category in results["industry_accuracy"]:
                data = results["industry_accuracy"][category]
                data["accuracy"] = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error evaluating model: {str(e)}")
            raise
    
    async def _test_model_prediction(self, model_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Test model prediction on a single document"""
        try:
            content = document.get('extracted_text', '')[:1000]  # Limit content
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Analyze this document and provide structured JSON output."},
                    {"role": "user", "content": f"Analyze this document:\n\n{content}"}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            self.logger.error(f"Error testing model prediction: {str(e)}")
            return {"document_type": "unknown", "confidence_score": 0.0}
    
    async def _store_fine_tuning_job(self, job: FineTuningJob):
        """Store fine-tuning job in database"""
        try:
            query = """
            INSERT INTO fine_tuning_jobs 
            (job_id, model_name, training_file_id, validation_file_id, status, 
             created_at, finished_at, fine_tuned_model, hyperparameters, 
             training_tokens, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                job.job_id,
                job.model_name,
                job.training_file_id,
                job.validation_file_id,
                job.status.value,
                job.created_at,
                job.finished_at,
                job.fine_tuned_model,
                json.dumps(job.hyperparameters),
                job.training_tokens,
                job.error_message
            )
            
            await self.sql_service.execute_non_query(query, params)
            
        except Exception as e:
            self.logger.error(f"Error storing fine-tuning job: {str(e)}")
            raise
    
    async def get_training_cost_estimate(
        self, 
        model_name: str, 
        training_tokens: int
    ) -> Dict[str, float]:
        """Calculate training cost estimate"""
        try:
            if model_name not in self.supported_models:
                raise ValueError(f"Model {model_name} not supported")
            
            model_info = self.supported_models[model_name]
            
            training_cost = (training_tokens / 1000) * model_info["training_cost_per_1k_tokens"]
            hosting_cost_per_hour = model_info["hosting_cost_per_hour"]
            
            return {
                "model_name": model_name,
                "training_tokens": training_tokens,
                "training_cost": training_cost,
                "hosting_cost_per_hour": hosting_cost_per_hour,
                "estimated_training_hours": 2,  # Conservative estimate
                "estimated_total_cost": training_cost + (hosting_cost_per_hour * 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating cost estimate: {str(e)}")
            raise