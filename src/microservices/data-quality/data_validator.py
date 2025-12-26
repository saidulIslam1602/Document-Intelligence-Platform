"""
Data Quality Validation Service
Comprehensive data validation, profiling, and quality monitoring
"""

import asyncio
import logging
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from src.shared.config.settings import config_manager
from src.shared.storage.sql_service import SQLService
from src.shared.cache.redis_cache import cache_service

class ValidationRule(Enum):
    """Data validation rule types"""
    REQUIRED = "required"
    DATA_TYPE = "data_type"
    FORMAT = "format"
    RANGE = "range"
    PATTERN = "pattern"
    UNIQUE = "unique"
    REFERENTIAL = "referential"
    BUSINESS_LOGIC = "business_logic"

class QualityLevel(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"  # 95-100%
    GOOD = "good"           # 80-94%
    FAIR = "fair"           # 60-79%
    POOR = "poor"           # 40-59%
    CRITICAL = "critical"   # 0-39%

@dataclass
class ValidationResult:
    """Data validation result"""
    field_name: str
    rule_type: ValidationRule
    passed: bool
    message: str
    value: Any = None
    expected: Any = None
    severity: str = "error"

@dataclass
class QualityMetrics:
    """Data quality metrics"""
    completeness: float
    accuracy: float
    consistency: float
    validity: float
    timeliness: float
    uniqueness: float
    overall_score: float
    quality_level: QualityLevel

class DataValidator:
    """Advanced data validation and quality assessment"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.logger = logging.getLogger(__name__)
        
        # Validation rules registry
        self.validation_rules = {}
        self.quality_thresholds = {
            "excellent": 0.95,
            "good": 0.80,
            "fair": 0.60,
            "poor": 0.40
        }
    
    def register_validation_rule(self, table_name: str, field_name: str, 
                               rule: ValidationRule, config: Dict[str, Any]):
        """Register a validation rule for a field"""
        if table_name not in self.validation_rules:
            self.validation_rules[table_name] = {}
        
        if field_name not in self.validation_rules[table_name]:
            self.validation_rules[table_name][field_name] = []
        
        self.validation_rules[table_name][field_name].append({
            "rule": rule,
            "config": config
        })
    
    async def validate_document_data(self, document_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate document data against rules"""
        results = []
        
        # Required fields validation
        required_fields = ["document_id", "user_id", "file_name", "file_size", "content_type"]
        for field in required_fields:
            if field not in document_data or document_data[field] is None:
                results.append(ValidationResult(
                    field_name=field,
                    rule_type=ValidationRule.REQUIRED,
                    passed=False,
                    message=f"Required field {field} is missing",
                    severity="error"
                ))
        
        # Data type validation
        if "file_size" in document_data:
            try:
                int(document_data["file_size"])
                results.append(ValidationResult(
                    field_name="file_size",
                    rule_type=ValidationRule.DATA_TYPE,
                    passed=True,
                    message="File size is valid integer"
                ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    field_name="file_size",
                    rule_type=ValidationRule.DATA_TYPE,
                    passed=False,
                    message="File size must be a valid integer",
                    value=document_data["file_size"],
                    severity="error"
                ))
        
        # Format validation
        if "content_type" in document_data:
            valid_types = ["application/pdf", "image/jpeg", "image/png", "text/plain", "application/msword"]
            if document_data["content_type"] not in valid_types:
                results.append(ValidationResult(
                    field_name="content_type",
                    rule_type=ValidationRule.FORMAT,
                    passed=False,
                    message=f"Invalid content type: {document_data['content_type']}",
                    value=document_data["content_type"],
                    expected=valid_types,
                    severity="warning"
                ))
        
        # File size range validation
        if "file_size" in document_data:
            try:
                size = int(document_data["file_size"])
                if size <= 0:
                    results.append(ValidationResult(
                        field_name="file_size",
                        rule_type=ValidationRule.RANGE,
                        passed=False,
                        message="File size must be greater than 0",
                        value=size,
                        severity="error"
                    ))
                elif size > 100 * 1024 * 1024:  # 100MB limit
                    results.append(ValidationResult(
                        field_name="file_size",
                        rule_type=ValidationRule.RANGE,
                        passed=False,
                        message="File size exceeds 100MB limit",
                        value=size,
                        severity="warning"
                    ))
                else:
                    results.append(ValidationResult(
                        field_name="file_size",
                        rule_type=ValidationRule.RANGE,
                        passed=True,
                        message="File size is within acceptable range"
                    ))
            except (ValueError, TypeError):
                pass  # Already handled in data type validation
        
        return results
    
    async def validate_analytics_data(self, analytics_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate analytics data"""
        results = []
        
        # Required fields
        required_fields = ["metric_name", "metric_value", "metric_timestamp"]
        for field in required_fields:
            if field not in analytics_data or analytics_data[field] is None:
                results.append(ValidationResult(
                    field_name=field,
                    rule_type=ValidationRule.REQUIRED,
                    passed=False,
                    message=f"Required field {field} is missing",
                    severity="error"
                ))
        
        # Metric value validation
        if "metric_value" in analytics_data:
            try:
                value = float(analytics_data["metric_value"])
                if not (0 <= value <= 1):  # Assuming normalized metrics
                    results.append(ValidationResult(
                        field_name="metric_value",
                        rule_type=ValidationRule.RANGE,
                        passed=False,
                        message="Metric value should be between 0 and 1",
                        value=value,
                        severity="warning"
                    ))
                else:
                    results.append(ValidationResult(
                        field_name="metric_value",
                        rule_type=ValidationRule.RANGE,
                        passed=True,
                        message="Metric value is within valid range"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    field_name="metric_value",
                    rule_type=ValidationRule.DATA_TYPE,
                    passed=False,
                    message="Metric value must be a valid number",
                    value=analytics_data["metric_value"],
                    severity="error"
                ))
        
        return results
    
    async def calculate_quality_metrics(self, table_name: str, 
                                      sample_size: int = 1000) -> QualityMetrics:
        """Calculate comprehensive data quality metrics"""
        try:
            # Get sample data
            query = f"SELECT TOP {sample_size} * FROM {table_name}"
            data = self.sql_service.execute_query(query)
            
            if not data:
                return QualityMetrics(
                    completeness=0.0,
                    accuracy=0.0,
                    consistency=0.0,
                    validity=0.0,
                    timeliness=0.0,
                    uniqueness=0.0,
                    overall_score=0.0,
                    quality_level=QualityLevel.CRITICAL
                )
            
            df = pd.DataFrame(data)
            
            # Calculate completeness (non-null values)
            completeness = (1 - df.isnull().sum().sum() / (len(df) * len(df.columns)))
            
            # Calculate validity (data format compliance)
            validity_scores = []
            for column in df.columns:
                if column in ['created_at', 'updated_at', 'timestamp']:
                    # Check date format validity
                    try:
                        pd.to_datetime(df[column], errors='raise')
                        validity_scores.append(1.0)
                    except Exception as e:
                        self.logger.warning(f"Validation failed for column {column}: {str(e)}")
                        validity_scores.append(0.0)
                elif column in ['file_size']:
                    # Check numeric validity
                    try:
                        pd.to_numeric(df[column], errors='raise')
                        validity_scores.append(1.0)
                    except Exception as e:
                        self.logger.warning(f"Validation failed for column {column}: {str(e)}")
                        validity_scores.append(0.0)
                else:
                    # Check string validity (non-empty)
                    validity_scores.append((df[column].astype(str).str.len() > 0).mean())
            
            validity = np.mean(validity_scores) if validity_scores else 0.0
            
            # Calculate uniqueness (duplicate rate)
            uniqueness = 1 - (len(df) - len(df.drop_duplicates())) / len(df) if len(df) > 0 else 0.0
            
            # Calculate consistency (data type consistency)
            consistency_scores = []
            for column in df.columns:
                if column in ['file_size']:
                    # Check if all values are numeric
                    consistency_scores.append(pd.to_numeric(df[column], errors='coerce').notna().mean())
                elif column in ['created_at', 'updated_at', 'timestamp']:
                    # Check if all values are valid dates
                    consistency_scores.append(pd.to_datetime(df[column], errors='coerce').notna().mean())
                else:
                    # Check if all values are strings
                    consistency_scores.append(df[column].astype(str).str.len().gt(0).mean())
            
            consistency = np.mean(consistency_scores) if consistency_scores else 0.0
            
            # Calculate accuracy (business rule compliance)
            accuracy = await self._calculate_accuracy_score(df, table_name)
            
            # Calculate timeliness (data freshness)
            timeliness = await self._calculate_timeliness_score(df, table_name)
            
            # Calculate overall score
            overall_score = np.mean([
                completeness, accuracy, consistency, validity, timeliness, uniqueness
            ])
            
            # Determine quality level
            if overall_score >= self.quality_thresholds["excellent"]:
                quality_level = QualityLevel.EXCELLENT
            elif overall_score >= self.quality_thresholds["good"]:
                quality_level = QualityLevel.GOOD
            elif overall_score >= self.quality_thresholds["fair"]:
                quality_level = QualityLevel.FAIR
            elif overall_score >= self.quality_thresholds["poor"]:
                quality_level = QualityLevel.POOR
            else:
                quality_level = QualityLevel.CRITICAL
            
            return QualityMetrics(
                completeness=round(completeness, 3),
                accuracy=round(accuracy, 3),
                consistency=round(consistency, 3),
                validity=round(validity, 3),
                timeliness=round(timeliness, 3),
                uniqueness=round(uniqueness, 3),
                overall_score=round(overall_score, 3),
                quality_level=quality_level
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating quality metrics: {str(e)}")
            return QualityMetrics(
                completeness=0.0,
                accuracy=0.0,
                consistency=0.0,
                validity=0.0,
                timeliness=0.0,
                uniqueness=0.0,
                overall_score=0.0,
                quality_level=QualityLevel.CRITICAL
            )
    
    async def _calculate_accuracy_score(self, df: pd.DataFrame, table_name: str) -> float:
        """Calculate accuracy score based on business rules"""
        try:
            if table_name == "documents":
                # Business rules for documents
                accuracy_scores = []
                
                # File size should be positive
                if 'file_size' in df.columns:
                    accuracy_scores.append((df['file_size'] > 0).mean())
                
                # Content type should be valid
                if 'content_type' in df.columns:
                    valid_types = ["application/pdf", "image/jpeg", "image/png", "text/plain"]
                    accuracy_scores.append(df['content_type'].isin(valid_types).mean())
                
                # Document ID should be unique
                if 'document_id' in df.columns:
                    accuracy_scores.append((df['document_id'].nunique() / len(df)))
                
                return np.mean(accuracy_scores) if accuracy_scores else 0.0
            
            elif table_name == "analytics_metrics":
                # Business rules for analytics
                accuracy_scores = []
                
                # Metric value should be between 0 and 1
                if 'metric_value' in df.columns:
                    accuracy_scores.append(((df['metric_value'] >= 0) & (df['metric_value'] <= 1)).mean())
                
                # Metric name should not be empty
                if 'metric_name' in df.columns:
                    accuracy_scores.append(df['metric_name'].str.len().gt(0).mean())
                
                return np.mean(accuracy_scores) if accuracy_scores else 0.0
            
            return 0.5  # Default accuracy score
            
        except Exception as e:
            self.logger.error(f"Error calculating accuracy score: {str(e)}")
            return 0.0
    
    async def _calculate_timeliness_score(self, df: pd.DataFrame, table_name: str) -> float:
        """Calculate timeliness score based on data freshness"""
        try:
            timestamp_columns = ['created_at', 'updated_at', 'timestamp', 'metric_timestamp']
            timestamp_col = None
            
            for col in timestamp_columns:
                if col in df.columns:
                    timestamp_col = col
                    break
            
            if timestamp_col is None:
                return 0.5  # Default timeliness score
            
            # Convert to datetime
            timestamps = pd.to_datetime(df[timestamp_col], errors='coerce')
            now = pd.Timestamp.now()
            
            # Calculate age in hours
            age_hours = (now - timestamps).dt.total_seconds() / 3600
            
            # Timeliness score: 1.0 for data < 1 hour old, decreasing to 0.0 for data > 24 hours old
            timeliness = np.clip(1 - (age_hours / 24), 0, 1)
            
            return timeliness.mean()
            
        except Exception as e:
            self.logger.error(f"Error calculating timeliness score: {str(e)}")
            return 0.0
    
    async def generate_quality_report(self, table_name: str) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        try:
            # Calculate quality metrics
            metrics = await self.calculate_quality_metrics(table_name)
            
            # Get validation results
            validation_results = await self._get_validation_results(table_name)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(metrics, validation_results)
            
            return {
                "table_name": table_name,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "completeness": metrics.completeness,
                    "accuracy": metrics.accuracy,
                    "consistency": metrics.consistency,
                    "validity": metrics.validity,
                    "timeliness": metrics.timeliness,
                    "uniqueness": metrics.uniqueness,
                    "overall_score": metrics.overall_score,
                    "quality_level": metrics.quality_level.value
                },
                "validation_results": [
                    {
                        "field_name": result.field_name,
                        "rule_type": result.rule_type.value,
                        "passed": result.passed,
                        "message": result.message,
                        "severity": result.severity
                    }
                    for result in validation_results
                ],
                "recommendations": recommendations,
                "summary": {
                    "total_validations": len(validation_results),
                    "passed_validations": sum(1 for r in validation_results if r.passed),
                    "failed_validations": sum(1 for r in validation_results if not r.passed),
                    "critical_issues": sum(1 for r in validation_results if not r.passed and r.severity == "error")
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating quality report: {str(e)}")
            raise
    
    async def _get_validation_results(self, table_name: str) -> List[ValidationResult]:
        """Get validation results for a table"""
        # This would typically query validation results from a database
        # For now, return empty list
        return []
    
    async def _generate_recommendations(self, metrics: QualityMetrics, 
                                      validation_results: List[ValidationResult]) -> List[str]:
        """Generate data quality improvement recommendations"""
        recommendations = []
        
        if metrics.completeness < 0.8:
            recommendations.append("Improve data completeness by implementing required field validation")
        
        if metrics.accuracy < 0.8:
            recommendations.append("Enhance data accuracy by implementing business rule validation")
        
        if metrics.consistency < 0.8:
            recommendations.append("Improve data consistency by standardizing data formats")
        
        if metrics.validity < 0.8:
            recommendations.append("Enhance data validity by implementing format validation")
        
        if metrics.timeliness < 0.8:
            recommendations.append("Improve data timeliness by implementing real-time data processing")
        
        if metrics.uniqueness < 0.8:
            recommendations.append("Enhance data uniqueness by implementing duplicate detection")
        
        # Add specific recommendations based on validation results
        error_count = sum(1 for r in validation_results if not r.passed and r.severity == "error")
        if error_count > 0:
            recommendations.append(f"Address {error_count} critical validation errors")
        
        if not recommendations:
            recommendations.append("Data quality is excellent - maintain current standards")
        
        return recommendations

# Pydantic models for API
class ValidationRequest(BaseModel):
    table_name: str
    data: Dict[str, Any]

class QualityReportResponse(BaseModel):
    table_name: str
    timestamp: str
    metrics: Dict[str, Any]
    validation_results: List[Dict[str, Any]]
    recommendations: List[str]
    summary: Dict[str, Any]

# Global validator instance
data_validator = DataValidator()