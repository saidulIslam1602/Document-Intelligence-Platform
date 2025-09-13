"""
Fine-Tuning Workflow Orchestrator
Manages end-to-end fine-tuning workflows for document intelligence
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

from .fine_tuning_service import DocumentFineTuningService, FineTuningStatus, FineTuningJob
from ...shared.events.event_sourcing import DomainEvent, EventType, EventBus
from ...shared.storage.sql_service import SQLService
from ...shared.config.settings import config_manager

class WorkflowStatus(Enum):
    """Workflow status enumeration"""
    PENDING = "pending"
    DATA_PREPARATION = "data_preparation"
    TRAINING = "training"
    EVALUATION = "evaluation"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"
    FAILED = "failed"

class DataQualityLevel(Enum):
    """Data quality level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXCELLENT = "excellent"

@dataclass
class WorkflowStep:
    """Workflow step data structure"""
    step_id: str
    name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metrics: Dict[str, Any]

@dataclass
class FineTuningWorkflow:
    """Fine-tuning workflow data structure"""
    workflow_id: str
    name: str
    description: str
    status: WorkflowStatus
    model_name: str
    document_type: str
    industry: str
    steps: List[WorkflowStep]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    metrics: Dict[str, Any]

class DocumentFineTuningWorkflow:
    """End-to-end fine-tuning workflow orchestrator"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.fine_tuning_service = DocumentFineTuningService(event_bus)
        self.sql_service = SQLService(self.config.sql_connection_string)
        
        # Workflow steps configuration
        self.workflow_steps = [
            "data_collection",
            "data_quality_assessment",
            "data_preprocessing",
            "training_data_preparation",
            "model_training",
            "model_evaluation",
            "model_deployment",
            "performance_monitoring"
        ]
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        model_name: str,
        document_type: str,
        industry: str,
        target_accuracy: float = 0.85,
        max_training_time_hours: int = 24
    ) -> FineTuningWorkflow:
        """Create a new fine-tuning workflow"""
        try:
            workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Initialize workflow steps
            steps = []
            for step_id in self.workflow_steps:
                step = WorkflowStep(
                    step_id=step_id,
                    name=step_id.replace('_', ' ').title(),
                    status="pending",
                    started_at=None,
                    completed_at=None,
                    error_message=None,
                    metrics={}
                )
                steps.append(step)
            
            # Create workflow
            workflow = FineTuningWorkflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                status=WorkflowStatus.PENDING,
                model_name=model_name,
                document_type=document_type,
                industry=industry,
                steps=steps,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                completed_at=None,
                metrics={
                    "target_accuracy": target_accuracy,
                    "max_training_time_hours": max_training_time_hours,
                    "current_accuracy": 0.0,
                    "training_tokens": 0,
                    "estimated_cost": 0.0
                }
            )
            
            # Store workflow in database
            await self._store_workflow(workflow)
            
            # Publish event
            if self.event_bus:
                await self.event_bus.publish(DomainEvent(
                    event_type=EventType.WORKFLOW_CREATED,
                    aggregate_id=workflow_id,
                    event_data={
                        "workflow_id": workflow_id,
                        "name": name,
                        "model_name": model_name,
                        "document_type": document_type,
                        "industry": industry
                    }
                ))
            
            self.logger.info(f"Created fine-tuning workflow: {workflow_id}")
            return workflow
            
        except Exception as e:
            self.logger.error(f"Error creating workflow: {str(e)}")
            raise
    
    async def execute_workflow(self, workflow_id: str) -> FineTuningWorkflow:
        """Execute the complete fine-tuning workflow"""
        try:
            workflow = await self._get_workflow(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            self.logger.info(f"Starting workflow execution: {workflow_id}")
            
            # Update workflow status
            workflow.status = WorkflowStatus.DATA_PREPARATION
            await self._update_workflow(workflow)
            
            # Step 1: Data Collection
            await self._execute_step(workflow, "data_collection", self._collect_training_data)
            
            # Step 2: Data Quality Assessment
            await self._execute_step(workflow, "data_quality_assessment", self._assess_data_quality)
            
            # Step 3: Data Preprocessing
            await self._execute_step(workflow, "data_preprocessing", self._preprocess_data)
            
            # Step 4: Training Data Preparation
            await self._execute_step(workflow, "training_data_preparation", self._prepare_training_data)
            
            # Step 5: Model Training
            await self._execute_step(workflow, "model_training", self._train_model)
            
            # Step 6: Model Evaluation
            await self._execute_step(workflow, "model_evaluation", self._evaluate_model)
            
            # Step 7: Model Deployment
            await self._execute_step(workflow, "model_deployment", self._deploy_model)
            
            # Step 8: Performance Monitoring
            await self._execute_step(workflow, "performance_monitoring", self._setup_monitoring)
            
            # Complete workflow
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            await self._update_workflow(workflow)
            
            self.logger.info(f"Workflow completed successfully: {workflow_id}")
            return workflow
            
        except Exception as e:
            self.logger.error(f"Error executing workflow: {str(e)}")
            workflow.status = WorkflowStatus.FAILED
            await self._update_workflow(workflow)
            raise
    
    async def _execute_step(
        self, 
        workflow: FineTuningWorkflow, 
        step_id: str, 
        step_function
    ):
        """Execute a workflow step"""
        try:
            step = next(s for s in workflow.steps if s.step_id == step_id)
            step.status = "running"
            step.started_at = datetime.now()
            await self._update_workflow(workflow)
            
            self.logger.info(f"Executing step: {step_id}")
            
            # Execute step function
            result = await step_function(workflow)
            
            # Update step status
            step.status = "completed"
            step.completed_at = datetime.now()
            step.metrics.update(result.get("metrics", {}))
            workflow.updated_at = datetime.now()
            
            await self._update_workflow(workflow)
            
            self.logger.info(f"Step completed: {step_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing step {step_id}: {str(e)}")
            step.status = "failed"
            step.error_message = str(e)
            step.completed_at = datetime.now()
            await self._update_workflow(workflow)
            raise
    
    async def _collect_training_data(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Collect training data for the workflow"""
        try:
            # Query documents from database
            query = """
            SELECT document_id, extracted_text, document_type, industry, 
                   entities, summary, confidence, created_at, file_path
            FROM processed_documents 
            WHERE document_type = ? AND industry = ? 
            AND confidence > 0.7
            ORDER BY created_at DESC
            """
            
            documents = await self.sql_service.execute_query(
                query, 
                (workflow.document_type, workflow.industry)
            )
            
            # Filter and validate documents
            valid_documents = []
            for doc in documents:
                if self._validate_document_for_training(doc):
                    valid_documents.append(doc)
            
            # Store collected data in workflow
            workflow.metrics["collected_documents"] = len(valid_documents)
            workflow.metrics["total_documents_available"] = len(documents)
            
            return {
                "metrics": {
                    "collected_documents": len(valid_documents),
                    "total_documents_available": len(documents),
                    "collection_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting training data: {str(e)}")
            raise
    
    async def _assess_data_quality(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Assess quality of collected training data"""
        try:
            # Get collected documents
            documents = await self._get_workflow_documents(workflow)
            
            if not documents:
                raise ValueError("No documents available for quality assessment")
            
            # Assess data quality metrics
            quality_metrics = await self._calculate_data_quality_metrics(documents)
            
            # Determine overall quality level
            quality_level = self._determine_quality_level(quality_metrics)
            
            # Update workflow metrics
            workflow.metrics.update(quality_metrics)
            workflow.metrics["data_quality_level"] = quality_level.value
            
            return {
                "metrics": quality_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing data quality: {str(e)}")
            raise
    
    async def _preprocess_data(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Preprocess training data"""
        try:
            # Get documents
            documents = await self._get_workflow_documents(workflow)
            
            # Apply preprocessing steps
            preprocessed_docs = []
            for doc in documents:
                processed_doc = await self._preprocess_document(doc)
                preprocessed_docs.append(processed_doc)
            
            # Store preprocessed data
            await self._store_preprocessed_data(workflow.workflow_id, preprocessed_docs)
            
            workflow.metrics["preprocessed_documents"] = len(preprocessed_docs)
            
            return {
                "metrics": {
                    "preprocessed_documents": len(preprocessed_docs),
                    "preprocessing_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error preprocessing data: {str(e)}")
            raise
    
    async def _prepare_training_data(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Prepare training data for fine-tuning"""
        try:
            # Get preprocessed documents
            documents = await self._get_preprocessed_data(workflow.workflow_id)
            
            # Prepare training and validation files
            training_file_id, validation_file_id = await self.fine_tuning_service.prepare_training_data(
                documents=documents,
                document_type=workflow.document_type,
                industry=workflow.industry,
                min_samples=50
            )
            
            # Store file IDs
            workflow.metrics["training_file_id"] = training_file_id
            workflow.metrics["validation_file_id"] = validation_file_id
            
            return {
                "metrics": {
                    "training_file_id": training_file_id,
                    "validation_file_id": validation_file_id,
                    "preparation_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {str(e)}")
            raise
    
    async def _train_model(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Train the fine-tuned model"""
        try:
            # Get training file IDs
            training_file_id = workflow.metrics.get("training_file_id")
            validation_file_id = workflow.metrics.get("validation_file_id")
            
            if not training_file_id:
                raise ValueError("Training file ID not found")
            
            # Create fine-tuning job
            job = await self.fine_tuning_service.create_fine_tuning_job(
                model_name=workflow.model_name,
                training_file_id=training_file_id,
                validation_file_id=validation_file_id,
                hyperparameters={
                    "n_epochs": 3,
                    "batch_size": 4,
                    "learning_rate_multiplier": 0.1
                },
                suffix=f"{workflow.document_type}_{workflow.industry}"
            )
            
            # Store job ID
            workflow.metrics["fine_tuning_job_id"] = job.job_id
            
            # Monitor training progress
            await self._monitor_training_progress(workflow, job.job_id)
            
            return {
                "metrics": {
                    "fine_tuning_job_id": job.job_id,
                    "training_started_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}")
            raise
    
    async def _evaluate_model(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Evaluate the fine-tuned model"""
        try:
            # Get fine-tuned model name
            job_id = workflow.metrics.get("fine_tuning_job_id")
            if not job_id:
                raise ValueError("Fine-tuning job ID not found")
            
            job = await self.fine_tuning_service.get_fine_tuning_job(job_id)
            if not job.fine_tuned_model:
                raise ValueError("Fine-tuned model not available")
            
            # Get test documents
            test_documents = await self._get_test_documents(workflow)
            
            # Evaluate model
            evaluation_results = await self.fine_tuning_service.evaluate_fine_tuned_model(
                model_name=job.fine_tuned_model,
                test_documents=test_documents
            )
            
            # Update workflow metrics
            workflow.metrics.update(evaluation_results)
            workflow.metrics["fine_tuned_model"] = job.fine_tuned_model
            
            return {
                "metrics": evaluation_results
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating model: {str(e)}")
            raise
    
    async def _deploy_model(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Deploy the fine-tuned model"""
        try:
            model_name = workflow.metrics.get("fine_tuned_model")
            if not model_name:
                raise ValueError("Fine-tuned model name not found")
            
            # Deploy model
            deployment_name = f"{workflow.workflow_id}_deployment"
            deployment_id = await self.fine_tuning_service.deploy_fine_tuned_model(
                model_name=model_name,
                deployment_name=deployment_name,
                deployment_type="standard"
            )
            
            workflow.metrics["deployment_id"] = deployment_id
            workflow.metrics["deployment_name"] = deployment_name
            
            return {
                "metrics": {
                    "deployment_id": deployment_id,
                    "deployment_name": deployment_name,
                    "deployment_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error deploying model: {str(e)}")
            raise
    
    async def _setup_monitoring(self, workflow: FineTuningWorkflow) -> Dict[str, Any]:
        """Setup performance monitoring for the deployed model"""
        try:
            # Setup monitoring configuration
            monitoring_config = {
                "model_name": workflow.metrics.get("fine_tuned_model"),
                "deployment_id": workflow.metrics.get("deployment_id"),
                "monitoring_enabled": True,
                "alert_thresholds": {
                    "accuracy": 0.8,
                    "response_time": 5.0,
                    "error_rate": 0.05
                }
            }
            
            # Store monitoring configuration
            await self._store_monitoring_config(workflow.workflow_id, monitoring_config)
            
            return {
                "metrics": {
                    "monitoring_enabled": True,
                    "monitoring_setup_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error setting up monitoring: {str(e)}")
            raise
    
    # Helper methods
    def _validate_document_for_training(self, doc: Dict[str, Any]) -> bool:
        """Validate if document is suitable for training"""
        try:
            # Check required fields
            required_fields = ['extracted_text', 'document_type', 'industry', 'confidence']
            if not all(field in doc for field in required_fields):
                return False
            
            # Check confidence threshold
            if doc.get('confidence', 0) < 0.7:
                return False
            
            # Check text length
            text = doc.get('extracted_text', '')
            if len(text) < 100:  # Minimum text length
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _calculate_data_quality_metrics(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        try:
            total_docs = len(documents)
            if total_docs == 0:
                return {"quality_score": 0.0, "quality_level": "low"}
            
            # Calculate various quality metrics
            confidence_scores = [doc.get('confidence', 0) for doc in documents]
            text_lengths = [len(doc.get('extracted_text', '')) for doc in documents]
            
            avg_confidence = np.mean(confidence_scores)
            avg_text_length = np.mean(text_lengths)
            confidence_std = np.std(confidence_scores)
            
            # Calculate quality score
            quality_score = (
                avg_confidence * 0.4 +
                min(avg_text_length / 1000, 1.0) * 0.3 +
                max(0, 1 - confidence_std) * 0.3
            )
            
            return {
                "quality_score": quality_score,
                "avg_confidence": avg_confidence,
                "avg_text_length": avg_text_length,
                "confidence_std": confidence_std,
                "total_documents": total_docs
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating quality metrics: {str(e)}")
            return {"quality_score": 0.0, "quality_level": "low"}
    
    def _determine_quality_level(self, metrics: Dict[str, Any]) -> DataQualityLevel:
        """Determine data quality level based on metrics"""
        quality_score = metrics.get("quality_score", 0.0)
        
        if quality_score >= 0.9:
            return DataQualityLevel.EXCELLENT
        elif quality_score >= 0.8:
            return DataQualityLevel.HIGH
        elif quality_score >= 0.6:
            return DataQualityLevel.MEDIUM
        else:
            return DataQualityLevel.LOW
    
    async def _preprocess_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess a single document"""
        try:
            # Clean and normalize text
            text = doc.get('extracted_text', '')
            cleaned_text = self._clean_text(text)
            
            # Extract and normalize entities
            entities = doc.get('entities', {})
            normalized_entities = self._normalize_entities(entities)
            
            # Create preprocessed document
            processed_doc = {
                **doc,
                'extracted_text': cleaned_text,
                'entities': normalized_entities,
                'preprocessed_at': datetime.now().isoformat()
            }
            
            return processed_doc
            
        except Exception as e:
            self.logger.error(f"Error preprocessing document: {str(e)}")
            return doc
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep punctuation
        import re
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        
        return text.strip()
    
    def _normalize_entities(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize entity extraction results"""
        try:
            normalized = {}
            for key, value in entities.items():
                if isinstance(value, list):
                    normalized[key] = [str(item).strip() for item in value if item]
                else:
                    normalized[key] = str(value).strip() if value else ""
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing entities: {str(e)}")
            return entities
    
    async def _monitor_training_progress(self, workflow: FineTuningWorkflow, job_id: str):
        """Monitor training progress"""
        try:
            max_wait_time = workflow.metrics.get("max_training_time_hours", 24) * 3600
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                job = await self.fine_tuning_service.get_fine_tuning_job(job_id)
                
                if job.status in [FineTuningStatus.SUCCEEDED, FineTuningStatus.FAILED, FineTuningStatus.CANCELLED]:
                    workflow.metrics["training_status"] = job.status.value
                    workflow.metrics["training_completed_at"] = datetime.now().isoformat()
                    break
                
                await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            self.logger.error(f"Error monitoring training progress: {str(e)}")
            raise
    
    # Database operations
    async def _store_workflow(self, workflow: FineTuningWorkflow):
        """Store workflow in database"""
        try:
            query = """
            INSERT INTO fine_tuning_workflows 
            (workflow_id, name, description, status, model_name, document_type, 
             industry, steps, created_at, updated_at, completed_at, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                workflow.workflow_id,
                workflow.name,
                workflow.description,
                workflow.status.value,
                workflow.model_name,
                workflow.document_type,
                workflow.industry,
                json.dumps([step.__dict__ for step in workflow.steps]),
                workflow.created_at,
                workflow.updated_at,
                workflow.completed_at,
                json.dumps(workflow.metrics)
            )
            
            await self.sql_service.execute_non_query(query, params)
            
        except Exception as e:
            self.logger.error(f"Error storing workflow: {str(e)}")
            raise
    
    async def _update_workflow(self, workflow: FineTuningWorkflow):
        """Update workflow in database"""
        try:
            query = """
            UPDATE fine_tuning_workflows 
            SET status = ?, steps = ?, updated_at = ?, completed_at = ?, metrics = ?
            WHERE workflow_id = ?
            """
            
            params = (
                workflow.status.value,
                json.dumps([step.__dict__ for step in workflow.steps]),
                workflow.updated_at,
                workflow.completed_at,
                json.dumps(workflow.metrics),
                workflow.workflow_id
            )
            
            await self.sql_service.execute_non_query(query, params)
            
        except Exception as e:
            self.logger.error(f"Error updating workflow: {str(e)}")
            raise
    
    async def _get_workflow(self, workflow_id: str) -> Optional[FineTuningWorkflow]:
        """Get workflow from database"""
        try:
            query = """
            SELECT workflow_id, name, description, status, model_name, document_type,
                   industry, steps, created_at, updated_at, completed_at, metrics
            FROM fine_tuning_workflows 
            WHERE workflow_id = ?
            """
            
            result = await self.sql_service.execute_query(query, (workflow_id,))
            if not result:
                return None
            
            row = result[0]
            
            # Reconstruct workflow object
            workflow = FineTuningWorkflow(
                workflow_id=row['workflow_id'],
                name=row['name'],
                description=row['description'],
                status=WorkflowStatus(row['status']),
                model_name=row['model_name'],
                document_type=row['document_type'],
                industry=row['industry'],
                steps=[WorkflowStep(**step) for step in json.loads(row['steps'])],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                completed_at=row['completed_at'],
                metrics=json.loads(row['metrics'])
            )
            
            return workflow
            
        except Exception as e:
            self.logger.error(f"Error getting workflow: {str(e)}")
            return None
    
    # Additional helper methods would be implemented here
    async def _get_workflow_documents(self, workflow: FineTuningWorkflow) -> List[Dict[str, Any]]:
        """Get documents for workflow"""
        # Implementation would query database for workflow documents
        return []
    
    async def _store_preprocessed_data(self, workflow_id: str, documents: List[Dict[str, Any]]):
        """Store preprocessed data"""
        # Implementation would store preprocessed documents
        pass
    
    async def _get_preprocessed_data(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get preprocessed data"""
        # Implementation would retrieve preprocessed documents
        return []
    
    async def _get_test_documents(self, workflow: FineTuningWorkflow) -> List[Dict[str, Any]]:
        """Get test documents for evaluation"""
        # Implementation would get test documents
        return []
    
    async def _store_monitoring_config(self, workflow_id: str, config: Dict[str, Any]):
        """Store monitoring configuration"""
        # Implementation would store monitoring config
        pass