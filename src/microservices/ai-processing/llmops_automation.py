"""
Enhanced LLMOps with Automation Tracking
Extends existing fine-tuning workflows with automation metrics and optimization
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx

from .fine_tuning_service import DocumentFineTuningService
from .fine_tuning_workflow import DocumentFineTuningWorkflow
from src.shared.config.settings import config_manager
from src.shared.storage.sql_service import SQLService

logger = logging.getLogger(__name__)

@dataclass
class AutomationMetricsForModel:
    """Automation metrics for a fine-tuned model"""
    model_id: str
    model_name: str
    automation_rate: float  # % of fully automated invoices
    accuracy: float  # Extraction accuracy
    confidence: float  # Average confidence score
    completeness: float  # Average completeness score
    validation_pass_rate: float  # % passing validation
    processing_speed: float  # Seconds per document
    cost_per_document: float  # Cost in USD
    documents_processed: int
    timestamp: datetime

@dataclass
class ModelComparisonResult:
    """Comparison between baseline and fine-tuned model"""
    baseline_metrics: AutomationMetricsForModel
    fine_tuned_metrics: AutomationMetricsForModel
    improvement: Dict[str, float]
    recommendation: str
    confidence_level: str

class LLMOpsAutomationTracker:
    """Tracks and optimizes automation metrics for LLMOps"""
    
    def __init__(self, event_bus=None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.fine_tuning_service = DocumentFineTuningService(event_bus)
        self.fine_tuning_workflow = DocumentFineTuningWorkflow(event_bus)
    
    async def track_model_automation_metrics(
        self,
        model_id: str,
        model_name: str,
        test_documents: List[str]
    ) -> AutomationMetricsForModel:
        """Track automation metrics for a specific model"""
        try:
            start_time = datetime.utcnow()
            total_processed = 0
            fully_automated = 0
            total_confidence = 0.0
            total_completeness = 0.0
            validation_passes = 0
            total_processing_time = 0.0
            
            # Process test documents with the model
            for doc_id in test_documents:
                try:
                    # Process document (simulate or call actual API)
                    result = await self._process_document_with_model(
                        model_id,
                        doc_id
                    )
                    
                    total_processed += 1
                    total_confidence += result.get("confidence", 0.0)
                    total_completeness += result.get("completeness", 0.0)
                    total_processing_time += result.get("processing_time", 0.0)
                    
                    if result.get("validation_passed", False):
                        validation_passes += 1
                    
                    if result.get("fully_automated", False):
                        fully_automated += 1
                        
                except Exception as e:
                    logger.error(f"Error processing document {doc_id}: {str(e)}")
                    continue
            
            # Calculate metrics
            automation_rate = (fully_automated / total_processed * 100) if total_processed > 0 else 0.0
            avg_confidence = total_confidence / total_processed if total_processed > 0 else 0.0
            avg_completeness = total_completeness / total_processed if total_processed > 0 else 0.0
            validation_pass_rate = (validation_passes / total_processed * 100) if total_processed > 0 else 0.0
            avg_processing_speed = total_processing_time / total_processed if total_processed > 0 else 0.0
            
            # Estimate cost (simplified)
            cost_per_document = self._estimate_cost_per_document(model_name, avg_processing_speed)
            
            # Calculate accuracy from validation results
            accuracy = validation_pass_rate / 100.0  # Simplified
            
            metrics = AutomationMetricsForModel(
                model_id=model_id,
                model_name=model_name,
                automation_rate=automation_rate,
                accuracy=accuracy,
                confidence=avg_confidence,
                completeness=avg_completeness,
                validation_pass_rate=validation_pass_rate,
                processing_speed=avg_processing_speed,
                cost_per_document=cost_per_document,
                documents_processed=total_processed,
                timestamp=datetime.utcnow()
            )
            
            # Store metrics in database
            await self._store_model_metrics(metrics)
            
            logger.info(f"Tracked automation metrics for model {model_id}: {automation_rate:.2f}%")
            return metrics
            
        except Exception as e:
            logger.error(f"Error tracking model automation metrics: {str(e)}")
            raise
    
    async def compare_models(
        self,
        baseline_model_id: str,
        fine_tuned_model_id: str,
        test_documents: List[str]
    ) -> ModelComparisonResult:
        """Compare baseline and fine-tuned model performance"""
        try:
            # Track metrics for both models
            baseline_metrics = await self.track_model_automation_metrics(
                baseline_model_id,
                "baseline",
                test_documents
            )
            
            fine_tuned_metrics = await self.track_model_automation_metrics(
                fine_tuned_model_id,
                "fine-tuned",
                test_documents
            )
            
            # Calculate improvements
            improvement = {
                "automation_rate": fine_tuned_metrics.automation_rate - baseline_metrics.automation_rate,
                "accuracy": fine_tuned_metrics.accuracy - baseline_metrics.accuracy,
                "confidence": fine_tuned_metrics.confidence - baseline_metrics.confidence,
                "completeness": fine_tuned_metrics.completeness - baseline_metrics.completeness,
                "validation_pass_rate": fine_tuned_metrics.validation_pass_rate - baseline_metrics.validation_pass_rate,
                "processing_speed_improvement": (baseline_metrics.processing_speed - fine_tuned_metrics.processing_speed) / baseline_metrics.processing_speed * 100 if baseline_metrics.processing_speed > 0 else 0,
                "cost_reduction": (baseline_metrics.cost_per_document - fine_tuned_metrics.cost_per_document) / baseline_metrics.cost_per_document * 100 if baseline_metrics.cost_per_document > 0 else 0
            }
            
            # Generate recommendation
            recommendation = self._generate_recommendation(improvement)
            
            # Determine confidence level
            confidence_level = self._determine_confidence_level(
                fine_tuned_metrics.documents_processed,
                improvement
            )
            
            result = ModelComparisonResult(
                baseline_metrics=baseline_metrics,
                fine_tuned_metrics=fine_tuned_metrics,
                improvement=improvement,
                recommendation=recommendation,
                confidence_level=confidence_level
            )
            
            logger.info(f"Model comparison completed: {improvement['automation_rate']:.2f}% improvement")
            return result
            
        except Exception as e:
            logger.error(f"Error comparing models: {str(e)}")
            raise
    
    async def optimize_for_automation_goal(
        self,
        current_model_id: str,
        target_automation_rate: float = 90.0
    ) -> Dict[str, Any]:
        """Optimize model configuration to achieve automation goal"""
        try:
            # Get current performance
            current_metrics = await self._get_model_metrics(current_model_id)
            
            if not current_metrics:
                raise ValueError(f"No metrics found for model {current_model_id}")
            
            gap = target_automation_rate - current_metrics.get("automation_rate", 0.0)
            
            # Generate optimization recommendations
            recommendations = []
            
            # Check confidence threshold
            avg_confidence = current_metrics.get("confidence", 0.0)
            if avg_confidence < 0.90:
                recommendations.append({
                    "area": "confidence",
                    "current": avg_confidence,
                    "target": 0.90,
                    "action": "Increase training data diversity and quality",
                    "expected_impact": "+5-10% automation rate",
                    "priority": "high"
                })
            
            # Check completeness
            avg_completeness = current_metrics.get("completeness", 0.0)
            if avg_completeness < 0.95:
                recommendations.append({
                    "area": "completeness",
                    "current": avg_completeness,
                    "target": 0.95,
                    "action": "Add more examples with complete field extraction",
                    "expected_impact": "+3-7% automation rate",
                    "priority": "high"
                })
            
            # Check validation pass rate
            validation_pass_rate = current_metrics.get("validation_pass_rate", 0.0)
            if validation_pass_rate < 85.0:
                recommendations.append({
                    "area": "validation",
                    "current": validation_pass_rate,
                    "target": 85.0,
                    "action": "Review and optimize validation rules or improve data quality",
                    "expected_impact": "+2-5% automation rate",
                    "priority": "medium"
                })
            
            # Check processing speed
            processing_speed = current_metrics.get("processing_speed", 0.0)
            if processing_speed > 5.0:
                recommendations.append({
                    "area": "performance",
                    "current": processing_speed,
                    "target": 5.0,
                    "action": "Optimize model size or use batch processing",
                    "expected_impact": "Faster processing without accuracy loss",
                    "priority": "low"
                })
            
            # Generate fine-tuning plan
            fine_tuning_plan = {
                "recommended_training_examples": self._calculate_required_examples(gap),
                "suggested_hyperparameters": {
                    "learning_rate": 0.0001 if gap > 10 else 0.00005,
                    "batch_size": 16,
                    "epochs": self._calculate_epochs(gap)
                },
                "estimated_training_time_hours": self._estimate_training_time(gap),
                "estimated_cost_usd": self._estimate_fine_tuning_cost(gap)
            }
            
            return {
                "current_automation_rate": current_metrics.get("automation_rate", 0.0),
                "target_automation_rate": target_automation_rate,
                "gap": gap,
                "is_achievable": gap <= 15.0,  # Realistic improvement threshold
                "recommendations": recommendations,
                "fine_tuning_plan": fine_tuning_plan,
                "estimated_timeline_days": self._estimate_timeline(gap),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error optimizing for automation goal: {str(e)}")
            raise
    
    async def generate_automation_dashboard_data(
        self,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """Generate data for automation dashboard"""
        try:
            # Parse time range
            now = datetime.utcnow()
            if time_range == "24h":
                start_time = now - timedelta(days=1)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            elif time_range == "30d":
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=7)
            
            # Query automation metrics over time
            query = """
                SELECT 
                    DATE(timestamp) as date,
                    model_name,
                    AVG(automation_rate) as avg_automation_rate,
                    AVG(accuracy) as avg_accuracy,
                    AVG(confidence) as avg_confidence,
                    AVG(completeness) as avg_completeness,
                    AVG(processing_speed) as avg_processing_speed,
                    SUM(documents_processed) as total_documents
                FROM model_automation_metrics
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp), model_name
                ORDER BY date ASC, model_name
            """
            
            results = self.sql_service.execute_query(query, (start_time,))
            
            # Process results
            dashboard_data = {
                "time_range": time_range,
                "trends": [],
                "model_performance": {},
                "summary": {
                    "current_automation_rate": 0.0,
                    "goal_progress": 0.0,
                    "total_documents_processed": 0,
                    "active_models": 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if results:
                # Build trends
                for row in results:
                    dashboard_data["trends"].append({
                        "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                        "model_name": row["model_name"],
                        "automation_rate": round(row["avg_automation_rate"], 2),
                        "accuracy": round(row["avg_accuracy"], 3),
                        "confidence": round(row["avg_confidence"], 3),
                        "completeness": round(row["avg_completeness"], 3),
                        "processing_speed": round(row["avg_processing_speed"], 2),
                        "documents_processed": row["total_documents"]
                    })
                
                # Calculate summary
                latest_metrics = [r for r in results if r["date"] == max([r["date"] for r in results])]
                if latest_metrics:
                    dashboard_data["summary"]["current_automation_rate"] = round(
                        sum([m["avg_automation_rate"] for m in latest_metrics]) / len(latest_metrics), 2
                    )
                    dashboard_data["summary"]["goal_progress"] = min(
                        dashboard_data["summary"]["current_automation_rate"] / 90.0 * 100, 100.0
                    )
                    dashboard_data["summary"]["active_models"] = len(set([r["model_name"] for r in results]))
                
                dashboard_data["summary"]["total_documents_processed"] = sum([r["total_documents"] for r in results])
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error generating automation dashboard data: {str(e)}")
            raise
    
    # Helper methods
    
    async def _process_document_with_model(
        self,
        model_id: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Process document with specific model
        Real implementation that evaluates fine-tuned models
        """
        try:
            start_time = datetime.utcnow()
            
            # 1. Retrieve document from database
            document = await self._get_test_document(document_id)
            if not document:
                raise ValueError(f"Test document {document_id} not found")
            
            # 2. Process with fine-tuned model
            result = await self._invoke_fine_tuned_model(
                model_id,
                document["content"],
                document.get("document_type", "invoice")
            )
            
            # 3. Calculate metrics by comparing with ground truth
            ground_truth = document.get("ground_truth", {})
            metrics = self._calculate_accuracy_metrics(result, ground_truth)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "document_id": document_id,
                "model_id": model_id,
                "confidence": metrics["confidence"],
                "completeness": metrics["completeness"],
                "validation_passed": metrics["validation_passed"],
                "fully_automated": metrics["fully_automated"],
                "processing_time": processing_time,
                "accuracy": metrics["accuracy"]
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id} with model {model_id}: {e}")
            # Return conservative metrics for failed processing
            return {
                "document_id": document_id,
                "model_id": model_id,
                "confidence": 0.0,
                "completeness": 0.0,
                "validation_passed": False,
                "fully_automated": False,
                "processing_time": 0.0,
                "accuracy": 0.0,
                "error": str(e)
            }
    
    async def _get_test_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve test document from database"""
        try:
            # Query test documents table
            query = """
                SELECT 
                    id,
                    content,
                    document_type,
                    ground_truth,
                    created_at
                FROM fine_tuning_test_documents
                WHERE id = ?
            """
            results = self.sql_service.execute_query(query, (document_id,))
            
            if results:
                doc = results[0]
                # Parse ground_truth JSON if it's stored as string
                if isinstance(doc.get("ground_truth"), str):
                    import json
                    doc["ground_truth"] = json.loads(doc["ground_truth"])
                return doc
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving test document {document_id}: {e}")
            return None
    
    async def _invoke_fine_tuned_model(
        self,
        model_id: str,
        document_content: str,
        document_type: str
    ) -> Dict[str, Any]:
        """
        Invoke fine-tuned model for inference
        Calls Azure OpenAI with custom fine-tuned model
        """
        try:
            import httpx
            from src.shared.http import get_http_client
            
            # Get fine-tuned model deployment name
            deployment_name = await self._get_model_deployment_name(model_id)
            
            # Prepare prompt for the model
            prompt = self._create_evaluation_prompt(document_content, document_type)
            
            # Call Azure OpenAI with fine-tuned model
            client = get_http_client()
            response = await client.post(
                f"{self.config.openai_endpoint}/openai/deployments/{deployment_name}/completions",
                headers={
                    "api-key": self.config.openai_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.0  # Deterministic for evaluation
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            # Parse model output
            model_output = response.json()["choices"][0]["text"]
            extracted_data = self._parse_model_output(model_output, document_type)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error invoking model {model_id}: {e}")
            raise
    
    async def _get_model_deployment_name(self, model_id: str) -> str:
        """Get Azure OpenAI deployment name for fine-tuned model"""
        try:
            query = """
                SELECT deployment_name
                FROM fine_tuned_models
                WHERE id = ? AND status = 'deployed'
            """
            results = self.sql_service.execute_query(query, (model_id,))
            
            if results:
                return results[0]["deployment_name"]
            else:
                raise ValueError(f"No deployed model found for {model_id}")
                
        except Exception as e:
            logger.error(f"Error getting model deployment: {e}")
            raise
    
    def _create_evaluation_prompt(self, document_content: str, document_type: str) -> str:
        """Create evaluation prompt for the model"""
        if document_type == "invoice":
            return f"""Extract invoice data from the following document:

{document_content}

Extract the following fields and return as JSON:
- invoice_number
- invoice_date
- vendor_name
- total_amount
- line_items (array)

JSON output:"""
        else:
            return f"""Extract key information from the following {document_type}:

{document_content}

Return extracted data as JSON."""
    
    def _parse_model_output(self, output: str, document_type: str) -> Dict[str, Any]:
        """Parse model output into structured data"""
        try:
            import json
            # Try to extract JSON from output
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = output[json_start:json_end]
                return json.loads(json_str)
            else:
                logger.warning(f"Could not find JSON in model output: {output}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing model output as JSON: {e}")
            return {}
    
    def _calculate_accuracy_metrics(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate accuracy metrics by comparing predicted vs ground truth
        """
        if not ground_truth:
            # No ground truth available, use confidence heuristics
            field_count = len(predicted)
            return {
                "confidence": min(1.0, field_count / 5.0),  # Assuming 5 key fields
                "completeness": min(1.0, field_count / 5.0),
                "validation_passed": field_count >= 3,
                "fully_automated": field_count >= 4,
                "accuracy": 0.5  # Unknown without ground truth
            }
        
        # Calculate field-level accuracy
        total_fields = len(ground_truth)
        correct_fields = 0
        extracted_fields = 0
        
        for field, true_value in ground_truth.items():
            if field in predicted:
                extracted_fields += 1
                pred_value = predicted[field]
                
                # Normalize and compare
                if self._values_match(pred_value, true_value):
                    correct_fields += 1
        
        # Calculate metrics
        accuracy = correct_fields / total_fields if total_fields > 0 else 0.0
        completeness = extracted_fields / total_fields if total_fields > 0 else 0.0
        confidence = accuracy  # Confidence based on accuracy
        
        # Determine validation and automation status
        validation_passed = accuracy >= 0.85
        fully_automated = accuracy >= 0.90 and completeness >= 0.95
        
        return {
            "confidence": confidence,
            "completeness": completeness,
            "validation_passed": validation_passed,
            "fully_automated": fully_automated,
            "accuracy": accuracy
        }
    
    def _values_match(self, predicted: Any, ground_truth: Any) -> bool:
        """Check if predicted value matches ground truth"""
        # Normalize strings
        if isinstance(predicted, str) and isinstance(ground_truth, str):
            return predicted.strip().lower() == ground_truth.strip().lower()
        
        # Numeric comparison with tolerance
        if isinstance(predicted, (int, float)) and isinstance(ground_truth, (int, float)):
            return abs(float(predicted) - float(ground_truth)) < 0.01
        
        # Direct comparison
        return predicted == ground_truth
    
    def _estimate_cost_per_document(self, model_name: str, processing_time: float) -> float:
        """Estimate cost per document"""
        # Simplified cost estimation
        if "gpt-4" in model_name.lower():
            base_cost = 0.03  # $0.03 per document
        else:
            base_cost = 0.01  # $0.01 per document
        
        # Add processing time factor
        time_factor = processing_time / 5.0  # Normalized to 5 seconds
        return base_cost * (1 + time_factor * 0.2)
    
    async def _get_model_metrics(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get latest metrics for a model"""
        try:
            query = """
                SELECT *
                FROM model_automation_metrics
                WHERE model_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            results = self.sql_service.execute_query(query, (model_id,))
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting model metrics: {str(e)}")
            return None
    
    async def _store_model_metrics(self, metrics: AutomationMetricsForModel):
        """Store model metrics in database"""
        try:
            # Create table if not exists
            create_table_query = """
                CREATE TABLE IF NOT EXISTS model_automation_metrics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    model_id VARCHAR(255) NOT NULL,
                    model_name VARCHAR(255) NOT NULL,
                    automation_rate FLOAT NOT NULL,
                    accuracy FLOAT NOT NULL,
                    confidence FLOAT NOT NULL,
                    completeness FLOAT NOT NULL,
                    validation_pass_rate FLOAT NOT NULL,
                    processing_speed FLOAT NOT NULL,
                    cost_per_document FLOAT NOT NULL,
                    documents_processed INT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    INDEX idx_model_id (model_id),
                    INDEX idx_timestamp (timestamp)
                )
            """
            self.sql_service.execute_query(create_table_query)
            
            # Insert metrics
            insert_query = """
                INSERT INTO model_automation_metrics (
                    model_id, model_name, automation_rate, accuracy, confidence,
                    completeness, validation_pass_rate, processing_speed,
                    cost_per_document, documents_processed, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.sql_service.execute_query(
                insert_query,
                (
                    metrics.model_id,
                    metrics.model_name,
                    metrics.automation_rate,
                    metrics.accuracy,
                    metrics.confidence,
                    metrics.completeness,
                    metrics.validation_pass_rate,
                    metrics.processing_speed,
                    metrics.cost_per_document,
                    metrics.documents_processed,
                    metrics.timestamp
                )
            )
            
        except Exception as e:
            logger.error(f"Error storing model metrics: {str(e)}")
            raise
    
    def _generate_recommendation(self, improvement: Dict[str, float]) -> str:
        """Generate deployment recommendation"""
        automation_improvement = improvement.get("automation_rate", 0.0)
        accuracy_improvement = improvement.get("accuracy", 0.0)
        cost_reduction = improvement.get("cost_reduction", 0.0)
        
        if automation_improvement >= 5.0 and accuracy_improvement >= 0.05:
            return "STRONGLY RECOMMENDED: Deploy fine-tuned model. Significant improvements in automation and accuracy."
        elif automation_improvement >= 3.0:
            return "RECOMMENDED: Deploy fine-tuned model. Good improvement in automation rate."
        elif automation_improvement >= 1.0:
            return "CONSIDER: Fine-tuned model shows improvement but may need more training."
        else:
            return "NOT RECOMMENDED: Continue fine-tuning with more diverse training data."
    
    def _determine_confidence_level(self, sample_size: int, improvement: Dict[str, float]) -> str:
        """Determine confidence level for comparison"""
        if sample_size >= 100:
            if improvement.get("automation_rate", 0.0) >= 5.0:
                return "HIGH"
            elif improvement.get("automation_rate", 0.0) >= 3.0:
                return "MEDIUM"
        elif sample_size >= 50:
            return "MEDIUM"
        
        return "LOW"
    
    def _calculate_required_examples(self, gap: float) -> int:
        """Calculate required training examples"""
        # Rule of thumb: 50 examples per 1% improvement needed
        return max(int(gap * 50), 100)
    
    def _calculate_epochs(self, gap: float) -> int:
        """Calculate recommended epochs"""
        if gap > 10:
            return 5
        elif gap > 5:
            return 3
        else:
            return 2
    
    def _estimate_training_time(self, gap: float) -> float:
        """Estimate training time in hours"""
        examples = self._calculate_required_examples(gap)
        epochs = self._calculate_epochs(gap)
        # Rough estimate: 1 hour per 500 examples per epoch
        return (examples * epochs) / 500.0
    
    def _estimate_fine_tuning_cost(self, gap: float) -> float:
        """Estimate fine-tuning cost in USD"""
        examples = self._calculate_required_examples(gap)
        epochs = self._calculate_epochs(gap)
        # Rough estimate: $0.008 per 1K tokens, average 1K tokens per example
        return examples * epochs * 0.008
    
    def _estimate_timeline(self, gap: float) -> int:
        """Estimate timeline in days"""
        training_time = self._estimate_training_time(gap)
        # Add data preparation and evaluation time
        total_time = training_time + 2.0  # +2 hours for prep and eval
        # Convert to days (assuming 8-hour work days)
        return max(int(total_time / 8.0) + 1, 1)

