"""
Data Quality Service
REST API for data validation, profiling, and quality monitoring
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .data_validator import data_validator, ValidationRequest, QualityReportResponse, QualityLevel
from ...shared.config.settings import config_manager
from ...shared.storage.sql_service import SQLService
from ...shared.cache.redis_cache import cache_service, cache_result

# Initialize FastAPI app
app = FastAPI(
    title="Data Quality Service",
    description="Comprehensive data validation, profiling, and quality monitoring",
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
class QualityMetricsRequest(BaseModel):
    table_name: str
    sample_size: int = Field(default=1000, ge=100, le=10000)

class ValidationRuleRequest(BaseModel):
    table_name: str
    field_name: str
    rule_type: str
    config: Dict[str, Any]

class QualityAlertRequest(BaseModel):
    table_name: str
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    enabled: bool = True

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "data-quality"
    }

# Data validation endpoints
@app.post("/validate/document")
async def validate_document_data(
    request: ValidationRequest,
    background_tasks: BackgroundTasks
):
    """Validate document data against quality rules"""
    try:
        results = await data_validator.validate_document_data(request.data)
        
        # Store validation results in background
        background_tasks.add_task(
            _store_validation_results,
            "documents",
            request.data.get("document_id", "unknown"),
            results
        )
        
        return {
            "document_id": request.data.get("document_id"),
            "validation_results": [
                {
                    "field_name": result.field_name,
                    "rule_type": result.rule_type.value,
                    "passed": result.passed,
                    "message": result.message,
                    "severity": result.severity
                }
                for result in results
            ],
            "summary": {
                "total_validations": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
                "critical_errors": sum(1 for r in results if not r.passed and r.severity == "error")
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating document data: {str(e)}")
        raise HTTPException(status_code=500, detail="Validation failed")

@app.post("/validate/analytics")
async def validate_analytics_data(
    request: ValidationRequest,
    background_tasks: BackgroundTasks
):
    """Validate analytics data against quality rules"""
    try:
        results = await data_validator.validate_analytics_data(request.data)
        
        # Store validation results in background
        background_tasks.add_task(
            _store_validation_results,
            "analytics_metrics",
            request.data.get("metric_name", "unknown"),
            results
        )
        
        return {
            "metric_name": request.data.get("metric_name"),
            "validation_results": [
                {
                    "field_name": result.field_name,
                    "rule_type": result.rule_type.value,
                    "passed": result.passed,
                    "message": result.message,
                    "severity": result.severity
                }
                for result in results
            ],
            "summary": {
                "total_validations": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
                "critical_errors": sum(1 for r in results if not r.passed and r.severity == "error")
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating analytics data: {str(e)}")
        raise HTTPException(status_code=500, detail="Validation failed")

# Data quality metrics endpoints
@app.post("/quality/metrics")
@cache_result(ttl=300, key_prefix="quality_metrics")  # Cache for 5 minutes
async def get_quality_metrics(request: QualityMetricsRequest):
    """Get comprehensive data quality metrics for a table"""
    try:
        metrics = await data_validator.calculate_quality_metrics(
            request.table_name, 
            request.sample_size
        )
        
        return {
            "table_name": request.table_name,
            "sample_size": request.sample_size,
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
            "interpretation": {
                "completeness": _interpret_metric(metrics.completeness, "completeness"),
                "accuracy": _interpret_metric(metrics.accuracy, "accuracy"),
                "consistency": _interpret_metric(metrics.consistency, "consistency"),
                "validity": _interpret_metric(metrics.validity, "validity"),
                "timeliness": _interpret_metric(metrics.timeliness, "timeliness"),
                "uniqueness": _interpret_metric(metrics.uniqueness, "uniqueness")
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting quality metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get quality metrics")

@app.post("/quality/report")
async def generate_quality_report(request: QualityMetricsRequest):
    """Generate comprehensive data quality report"""
    try:
        report = await data_validator.generate_quality_report(request.table_name)
        return report
        
    except Exception as e:
        logger.error(f"Error generating quality report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate quality report")

# Data profiling endpoints
@app.get("/profile/{table_name}")
@cache_result(ttl=600, key_prefix="data_profile")  # Cache for 10 minutes
async def profile_table(table_name: str, sample_size: int = 1000):
    """Generate data profile for a table"""
    try:
        # Get sample data
        query = f"SELECT TOP {sample_size} * FROM {table_name}"
        data = sql_service.execute_query(query)
        
        if not data:
            return {
                "table_name": table_name,
                "message": "No data found in table",
                "profile": {}
            }
        
        import pandas as pd
        df = pd.DataFrame(data)
        
        # Generate profile
        profile = {
            "table_name": table_name,
            "sample_size": len(df),
            "total_columns": len(df.columns),
            "columns": {}
        }
        
        for column in df.columns:
            col_data = df[column]
            col_profile = {
                "data_type": str(col_data.dtype),
                "non_null_count": col_data.count(),
                "null_count": col_data.isnull().sum(),
                "null_percentage": round((col_data.isnull().sum() / len(col_data)) * 100, 2),
                "unique_count": col_data.nunique(),
                "unique_percentage": round((col_data.nunique() / len(col_data)) * 100, 2)
            }
            
            # Add statistics based on data type
            if col_data.dtype in ['int64', 'float64']:
                col_profile.update({
                    "mean": round(col_data.mean(), 2) if not col_data.isnull().all() else None,
                    "median": round(col_data.median(), 2) if not col_data.isnull().all() else None,
                    "std": round(col_data.std(), 2) if not col_data.isnull().all() else None,
                    "min": col_data.min() if not col_data.isnull().all() else None,
                    "max": col_data.max() if not col_data.isnull().all() else None
                })
            elif col_data.dtype == 'object':
                col_profile.update({
                    "most_common": col_data.mode().iloc[0] if not col_data.mode().empty else None,
                    "most_common_count": col_data.value_counts().iloc[0] if not col_data.empty else 0,
                    "avg_length": round(col_data.astype(str).str.len().mean(), 2) if not col_data.isnull().all() else None
                })
            
            profile["columns"][column] = col_profile
        
        return profile
        
    except Exception as e:
        logger.error(f"Error profiling table {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to profile table")

# Quality monitoring endpoints
@app.get("/quality/dashboard")
@cache_result(ttl=60, key_prefix="quality_dashboard")  # Cache for 1 minute
async def get_quality_dashboard():
    """Get quality dashboard data for all tables"""
    try:
        tables = ["documents", "analytics_metrics", "users", "conversations"]
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "tables": {}
        }
        
        for table in tables:
            try:
                metrics = await data_validator.calculate_quality_metrics(table, 500)
                dashboard_data["tables"][table] = {
                    "overall_score": metrics.overall_score,
                    "quality_level": metrics.quality_level.value,
                    "completeness": metrics.completeness,
                    "accuracy": metrics.accuracy,
                    "consistency": metrics.consistency,
                    "validity": metrics.validity,
                    "timeliness": metrics.timeliness,
                    "uniqueness": metrics.uniqueness
                }
            except Exception as e:
                logger.warning(f"Could not get metrics for table {table}: {str(e)}")
                dashboard_data["tables"][table] = {
                    "overall_score": 0.0,
                    "quality_level": "critical",
                    "error": str(e)
                }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting quality dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get quality dashboard")

@app.get("/quality/alerts")
async def get_quality_alerts():
    """Get active data quality alerts"""
    try:
        # This would typically query alerts from a database
        # For now, return mock alerts
        alerts = [
            {
                "id": "alert_001",
                "table_name": "documents",
                "metric": "completeness",
                "value": 0.75,
                "threshold": 0.80,
                "severity": "warning",
                "message": "Document completeness below threshold",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "alert_002",
                "table_name": "analytics_metrics",
                "metric": "timeliness",
                "value": 0.60,
                "threshold": 0.80,
                "severity": "critical",
                "message": "Analytics data is stale",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["severity"] == "critical"]),
            "warning_alerts": len([a for a in alerts if a["severity"] == "warning"]),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Error getting quality alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get quality alerts")

# Helper functions
async def _store_validation_results(table_name: str, record_id: str, results: List):
    """Store validation results in database"""
    try:
        # This would store validation results in a database
        # For now, just log them
        logger.info(f"Stored validation results for {table_name}:{record_id}")
    except Exception as e:
        logger.error(f"Error storing validation results: {str(e)}")

def _interpret_metric(value: float, metric_name: str) -> str:
    """Interpret metric value and provide human-readable description"""
    if value >= 0.95:
        return f"Excellent {metric_name} - {value:.1%}"
    elif value >= 0.80:
        return f"Good {metric_name} - {value:.1%}"
    elif value >= 0.60:
        return f"Fair {metric_name} - {value:.1%}"
    elif value >= 0.40:
        return f"Poor {metric_name} - {value:.1%}"
    else:
        return f"Critical {metric_name} - {value:.1%}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)