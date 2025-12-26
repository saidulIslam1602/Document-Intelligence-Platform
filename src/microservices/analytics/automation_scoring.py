"""
Automation Scoring System
Tracks and calculates invoice automation metrics to achieve 90%+ automation goal for Compello AS
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from ...shared.storage.sql_service import SQLService
from ...shared.config.settings import config_manager
from ...shared.config.enhanced_settings import get_settings

logger = logging.getLogger(__name__)

@dataclass
class AutomationScore:
    """Automation score for a single invoice"""
    document_id: str
    confidence_score: float  # 0-1
    completeness_score: float  # 0-1
    validation_pass: bool
    automation_score: float  # confidence × completeness × validation_pass
    requires_review: bool
    timestamp: datetime

@dataclass
class AutomationMetrics:
    """Overall automation metrics"""
    automation_rate: float  # Percentage of fully automated invoices
    total_processed: int
    fully_automated: int
    requires_review: int
    manual_intervention: int
    average_confidence: float
    average_completeness: float
    validation_pass_rate: float
    time_range: str
    timestamp: datetime

class AutomationScoringEngine:
    """Engine for calculating and tracking automation scores"""
    
    def __init__(self, sql_service: SQLService = None):
        if sql_service:
            self.sql_service = sql_service
        else:
            config = config_manager.get_azure_config()
            self.sql_service = SQLService(config.sql_connection_string)
        
        # Get automation configuration from centralized settings
        settings = get_settings()
        self.automation_threshold = settings.automation.threshold
        self.confidence_threshold = settings.automation.confidence_threshold
        self.completeness_threshold = settings.automation.completeness_threshold
        self.automation_goal = settings.automation.goal
        self.validation_threshold = settings.automation.validation_threshold
        self.manual_intervention_threshold = settings.automation.manual_intervention_threshold
        
        logger.info(
            f"AutomationScoringEngine initialized with thresholds: "
            f"automation={self.automation_threshold}, "
            f"confidence={self.confidence_threshold}, "
            f"completeness={self.completeness_threshold}, "
            f"goal={self.automation_goal}"
        )
    
    def calculate_invoice_score(
        self,
        invoice_data: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> AutomationScore:
        """Calculate automation score for a single invoice"""
        try:
            # Calculate confidence score (from Form Recognizer)
            confidence_score = self._calculate_confidence_score(invoice_data)
            
            # Calculate completeness score (% of required fields extracted)
            completeness_score = self._calculate_completeness_score(invoice_data)
            
            # Check if validation passed
            validation_pass = validation_result.get("is_valid", False)
            
            # Calculate overall automation score
            # Formula: confidence × completeness × (1 if validation_pass else 0.5)
            validation_multiplier = 1.0 if validation_pass else 0.5
            automation_score = confidence_score * completeness_score * validation_multiplier
            
            # Determine if manual review is required
            requires_review = (
                automation_score < self.automation_threshold or
                confidence_score < self.confidence_threshold or
                completeness_score < self.completeness_threshold or
                not validation_pass
            )
            
            return AutomationScore(
                document_id=invoice_data.get("document_id", ""),
                confidence_score=confidence_score,
                completeness_score=completeness_score,
                validation_pass=validation_pass,
                automation_score=automation_score,
                requires_review=requires_review,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error calculating invoice score: {str(e)}")
            raise
    
    def _calculate_confidence_score(self, invoice_data: Dict[str, Any]) -> float:
        """Calculate confidence score from Form Recognizer results"""
        try:
            # Get confidence from invoice data
            overall_confidence = invoice_data.get("confidence", 0.0)
            
            # Also check field-level confidences
            field_confidences = []
            required_fields = [
                "vendor_name", "invoice_number", "total_amount",
                "invoice_date", "line_items"
            ]
            
            for field in required_fields:
                if field in invoice_data and invoice_data[field]:
                    # Field exists and has value
                    field_confidences.append(1.0)
                else:
                    field_confidences.append(0.0)
            
            # Average of overall confidence and field confidence
            field_confidence = sum(field_confidences) / len(field_confidences) if field_confidences else 0.0
            
            return (overall_confidence + field_confidence) / 2.0
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.0
    
    def _calculate_completeness_score(self, invoice_data: Dict[str, Any]) -> float:
        """Calculate completeness score (% of required fields extracted)"""
        try:
            required_fields = [
                "vendor_name",
                "invoice_number",
                "total_amount",
                "invoice_date",
                "line_items"
            ]
            
            optional_fields = [
                "vendor_address",
                "customer_name",
                "customer_address",
                "due_date",
                "tax_amount",
                "subtotal"
            ]
            
            # Count required fields
            required_count = 0
            for field in required_fields:
                value = invoice_data.get(field)
                if value and self._is_valid_value(value):
                    required_count += 1
            
            # Count optional fields
            optional_count = 0
            for field in optional_fields:
                value = invoice_data.get(field)
                if value and self._is_valid_value(value):
                    optional_count += 1
            
            # Weighted score: 70% required, 30% optional
            required_score = (required_count / len(required_fields)) * 0.7
            optional_score = (optional_count / len(optional_fields)) * 0.3
            
            return required_score + optional_score
            
        except Exception as e:
            logger.error(f"Error calculating completeness score: {str(e)}")
            return 0.0
    
    def _is_valid_value(self, value: Any) -> bool:
        """Check if a value is valid (not empty/null/zero)"""
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True
    
    def calculate_automation_metrics(
        self,
        time_range: str = "24h"
    ) -> AutomationMetrics:
        """Calculate overall automation metrics for a time period"""
        try:
            # Parse time range
            now = datetime.utcnow()
            if time_range == "1h":
                start_time = now - timedelta(hours=1)
            elif time_range == "24h":
                start_time = now - timedelta(days=1)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            elif time_range == "30d":
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=1)
            
            # Query automation scores from database
            query = """
                SELECT 
                    document_id,
                    confidence_score,
                    completeness_score,
                    validation_pass,
                    automation_score,
                    requires_review,
                    created_at
                FROM automation_scores
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """
            
            results = self.sql_service.execute_query(query, (start_time,))
            
            if not results:
                return AutomationMetrics(
                    automation_rate=0.0,
                    total_processed=0,
                    fully_automated=0,
                    requires_review=0,
                    manual_intervention=0,
                    average_confidence=0.0,
                    average_completeness=0.0,
                    validation_pass_rate=0.0,
                    time_range=time_range,
                    timestamp=now
                )
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(results)
            
            # Calculate metrics
            total_processed = len(df)
            fully_automated = len(df[~df['requires_review']])
            requires_review = len(df[df['requires_review']])
            
            # Manual intervention is when automation score < threshold
            manual_intervention = len(df[df['automation_score'] < self.manual_intervention_threshold])
            
            # Calculate averages
            average_confidence = df['confidence_score'].mean()
            average_completeness = df['completeness_score'].mean()
            validation_pass_rate = (df['validation_pass'].sum() / total_processed) * 100
            
            # Calculate automation rate
            automation_rate = (fully_automated / total_processed) * 100
            
            return AutomationMetrics(
                automation_rate=automation_rate,
                total_processed=total_processed,
                fully_automated=fully_automated,
                requires_review=requires_review,
                manual_intervention=manual_intervention,
                average_confidence=average_confidence,
                average_completeness=average_completeness,
                validation_pass_rate=validation_pass_rate,
                time_range=time_range,
                timestamp=now
            )
            
        except Exception as e:
            logger.error(f"Error calculating automation metrics: {str(e)}")
            raise
    
    def store_automation_score(self, score: AutomationScore):
        """Store automation score in database"""
        try:
            # Create table if not exists
            create_table_query = """
                CREATE TABLE IF NOT EXISTS automation_scores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    document_id VARCHAR(255) NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    completeness_score FLOAT NOT NULL,
                    validation_pass BOOLEAN NOT NULL,
                    automation_score FLOAT NOT NULL,
                    requires_review BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    INDEX idx_document_id (document_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_automation_score (automation_score)
                )
            """
            self.sql_service.execute_query(create_table_query)
            
            # Insert automation score
            insert_query = """
                INSERT INTO automation_scores (
                    document_id,
                    confidence_score,
                    completeness_score,
                    validation_pass,
                    automation_score,
                    requires_review,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            self.sql_service.execute_query(
                insert_query,
                (
                    score.document_id,
                    score.confidence_score,
                    score.completeness_score,
                    score.validation_pass,
                    score.automation_score,
                    score.requires_review,
                    score.timestamp
                )
            )
            
            logger.info(f"Stored automation score for document {score.document_id}: {score.automation_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error storing automation score: {str(e)}")
            raise
    
    def check_automation_goal(self, automation_rate: float) -> Dict[str, Any]:
        """Check if automation goal is being met"""
        # Use configurable goal instead of hardcoded value
        goal = self.automation_goal * 100  # Convert from 0.90 to 90.0
        is_met = automation_rate >= goal
        gap = goal - automation_rate if not is_met else 0.0
        
        status = "on_track" if automation_rate >= (goal - 5.0) else "needs_attention"
        if automation_rate < (goal - 10.0):
            status = "critical"
        
        return {
            "goal": goal,
            "current_rate": automation_rate,
            "is_met": is_met,
            "gap": gap,
            "status": status,
            "message": self._get_status_message(automation_rate, goal)
        }
    
    def _get_status_message(self, current_rate: float, goal: float) -> str:
        """Get status message based on automation rate"""
        if current_rate >= goal:
            return f"🎉 Automation goal achieved! Current rate: {current_rate:.1f}%"
        elif current_rate >= (goal - 5.0):
            return f"✅ On track to meet goal. Current rate: {current_rate:.1f}%, Gap: {goal - current_rate:.1f}%"
        elif current_rate >= (goal - 10.0):
            return f"⚠️ Needs attention. Current rate: {current_rate:.1f}%, Gap: {goal - current_rate:.1f}%"
        else:
            return f"🚨 Critical. Significant gap in automation. Current rate: {current_rate:.1f}%, Gap: {goal - current_rate:.1f}%"
    
    def get_automation_insights(
        self,
        time_range: str = "7d"
    ) -> List[Dict[str, Any]]:
        """Get insights and recommendations for improving automation"""
        try:
            metrics = self.calculate_automation_metrics(time_range)
            insights = []
            
            # Check confidence scores
            if metrics.average_confidence < self.confidence_threshold:
                insights.append({
                    "type": "confidence",
                    "priority": "high",
                    "message": f"Average confidence score ({metrics.average_confidence:.1%}) is below threshold ({self.confidence_threshold:.1%})",
                    "recommendation": "Consider fine-tuning Form Recognizer model or improving document quality"
                })
            
            # Check completeness scores
            if metrics.average_completeness < self.completeness_threshold:
                insights.append({
                    "type": "completeness",
                    "priority": "high",
                    "message": f"Average completeness score ({metrics.average_completeness:.1%}) is below threshold ({self.completeness_threshold:.1%})",
                    "recommendation": "Review document templates and ensure all required fields are present"
                })
            
            # Check validation pass rate
            validation_threshold_pct = self.validation_threshold * 100
            if metrics.validation_pass_rate < validation_threshold_pct:
                insights.append({
                    "type": "validation",
                    "priority": "medium",
                    "message": f"Validation pass rate ({metrics.validation_pass_rate:.1f}%) is below {validation_threshold_pct:.0f}%",
                    "recommendation": "Review and optimize data quality validation rules"
                })
            
            # Check automation rate
            goal_check = self.check_automation_goal(metrics.automation_rate)
            if not goal_check["is_met"]:
                insights.append({
                    "type": "automation_rate",
                    "priority": "critical" if goal_check["status"] == "critical" else "high",
                    "message": goal_check["message"],
                    "recommendation": f"Focus on improving confidence, completeness, and validation to close {goal_check['gap']:.1f}% gap"
                })
            
            # Check manual intervention rate
            manual_rate = (metrics.manual_intervention / metrics.total_processed) * 100 if metrics.total_processed > 0 else 0
            # Calculate acceptable manual intervention rate from automation goal
            max_manual_rate = (1.0 - self.automation_goal) * 100
            if manual_rate > max_manual_rate:
                insights.append({
                    "type": "manual_intervention",
                    "priority": "medium",
                    "message": f"{manual_rate:.1f}% of invoices require significant manual intervention (threshold: {max_manual_rate:.1f}%)",
                    "recommendation": "Identify common patterns in low-scoring invoices and create targeted training data"
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting automation insights: {str(e)}")
            return []

