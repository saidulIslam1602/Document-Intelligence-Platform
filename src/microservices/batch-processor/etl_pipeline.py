"""
ETL/ELT Batch Processing Pipeline
Comprehensive data transformation and loading workflows
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from src.shared.config.settings import config_manager
from src.shared.storage.sql_service import SQLService
from src.shared.storage.data_lake_service import DataLakeService
from src.shared.cache.redis_cache import cache_service

class PipelineStatus(Enum):
    """ETL Pipeline status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TransformationType(Enum):
    """Data transformation types"""
    CLEAN = "clean"
    ENRICH = "enrich"
    AGGREGATE = "aggregate"
    NORMALIZE = "normalize"
    VALIDATE = "validate"
    DEDUPLICATE = "deduplicate"

@dataclass
class PipelineStep:
    """ETL Pipeline step definition"""
    step_id: str
    step_name: str
    transformation_type: TransformationType
    source_query: str
    target_table: str
    transformation_config: Dict[str, Any]
    dependencies: List[str] = None
    enabled: bool = True

@dataclass
class PipelineExecution:
    """ETL Pipeline execution record"""
    execution_id: str
    pipeline_name: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    records_processed: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    execution_log: List[str] = None

class ETLPipeline:
    """Advanced ETL/ELT pipeline processor"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.data_lake_service = DataLakeService(self.config.data_lake_connection_string)
        self.logger = logging.getLogger(__name__)
        
        # Pipeline definitions
        self.pipelines = {}
        self.executions = {}
        
        # Initialize default pipelines
        self._initialize_default_pipelines()
    
    def _initialize_default_pipelines(self):
        """Initialize default ETL pipelines"""
        
        # Document Processing Pipeline
        self.pipelines["document_processing"] = [
            PipelineStep(
                step_id="extract_documents",
                step_name="Extract Raw Documents",
                transformation_type=TransformationType.CLEAN,
                source_query="SELECT * FROM documents WHERE status = 'uploaded'",
                target_table="staging_documents",
                transformation_config={
                    "clean_columns": ["file_name", "content_type"],
                    "validate_required": ["document_id", "user_id", "file_name"],
                    "data_types": {
                        "file_size": "int64",
                        "created_at": "datetime64[ns]"
                    }
                }
            ),
            PipelineStep(
                step_id="enrich_documents",
                step_name="Enrich Document Metadata",
                transformation_type=TransformationType.ENRICH,
                source_query="SELECT * FROM staging_documents",
                target_table="enriched_documents",
                transformation_config={
                    "add_columns": {
                        "file_extension": "SUBSTRING(file_name, CHARINDEX('.', file_name) + 1, LEN(file_name))",
                        "file_category": "CASE WHEN content_type LIKE '%pdf%' THEN 'document' WHEN content_type LIKE '%image%' THEN 'image' ELSE 'other' END",
                        "size_category": "CASE WHEN file_size < 1024000 THEN 'small' WHEN file_size < 10485760 THEN 'medium' ELSE 'large' END"
                    }
                },
                dependencies=["extract_documents"]
            ),
            PipelineStep(
                step_id="aggregate_documents",
                step_name="Aggregate Document Statistics",
                transformation_type=TransformationType.AGGREGATE,
                source_query="SELECT * FROM enriched_documents",
                target_table="document_aggregates",
                transformation_config={
                    "group_by": ["user_id", "file_category", "size_category"],
                    "aggregations": {
                        "total_documents": "COUNT(*)",
                        "total_size": "SUM(file_size)",
                        "avg_size": "AVG(file_size)",
                        "latest_upload": "MAX(created_at)"
                    }
                },
                dependencies=["enrich_documents"]
            )
        ]
        
        # Analytics Processing Pipeline
        self.pipelines["analytics_processing"] = [
            PipelineStep(
                step_id="extract_metrics",
                step_name="Extract Raw Metrics",
                transformation_type=TransformationType.CLEAN,
                source_query="SELECT * FROM analytics_metrics WHERE metric_timestamp >= DATEADD(day, -1, GETDATE())",
                target_table="staging_metrics",
                transformation_config={
                    "clean_columns": ["metric_name", "metadata"],
                    "validate_required": ["metric_name", "metric_value", "metric_timestamp"],
                    "data_types": {
                        "metric_value": "float64",
                        "metric_timestamp": "datetime64[ns]"
                    }
                }
            ),
            PipelineStep(
                step_id="normalize_metrics",
                step_name="Normalize Metric Values",
                transformation_type=TransformationType.NORMALIZE,
                source_query="SELECT * FROM staging_metrics",
                target_table="normalized_metrics",
                transformation_config={
                    "normalization_method": "min_max",
                    "target_range": [0, 1],
                    "group_by": ["metric_name"]
                },
                dependencies=["extract_metrics"]
            ),
            PipelineStep(
                step_id="aggregate_metrics",
                step_name="Aggregate Metrics by Time",
                transformation_type=TransformationType.AGGREGATE,
                source_query="SELECT * FROM normalized_metrics",
                target_table="metric_aggregates",
                transformation_config={
                    "group_by": ["metric_name", "DATE(metric_timestamp)"],
                    "aggregations": {
                        "avg_value": "AVG(metric_value)",
                        "min_value": "MIN(metric_value)",
                        "max_value": "MAX(metric_value)",
                        "count": "COUNT(*)",
                        "std_value": "STDEV(metric_value)"
                    }
                },
                dependencies=["normalize_metrics"]
            )
        ]
        
        # User Analytics Pipeline
        self.pipelines["user_analytics"] = [
            PipelineStep(
                step_id="extract_user_data",
                step_name="Extract User Data",
                transformation_type=TransformationType.CLEAN,
                source_query="SELECT u.*, COUNT(d.id) as document_count FROM users u LEFT JOIN documents d ON u.id = d.user_id GROUP BY u.id, u.email, u.name, u.created_at, u.updated_at, u.is_active",
                target_table="staging_users",
                transformation_config={
                    "clean_columns": ["email", "name"],
                    "validate_required": ["id", "email"],
                    "data_types": {
                        "created_at": "datetime64[ns]",
                        "updated_at": "datetime64[ns]",
                        "is_active": "bool"
                    }
                }
            ),
            PipelineStep(
                step_id="enrich_user_activity",
                step_name="Enrich User Activity Data",
                transformation_type=TransformationType.ENRICH,
                source_query="SELECT * FROM staging_users",
                target_table="enriched_users",
                transformation_config={
                    "add_columns": {
                        "user_tier": "CASE WHEN document_count = 0 THEN 'new' WHEN document_count < 10 THEN 'basic' WHEN document_count < 50 THEN 'active' ELSE 'power' END",
                        "days_since_created": "DATEDIFF(day, created_at, GETDATE())",
                        "is_recent_user": "CASE WHEN DATEDIFF(day, created_at, GETDATE()) < 30 THEN 1 ELSE 0 END"
                    }
                },
                dependencies=["extract_user_data"]
            )
        ]
    
    async def execute_pipeline(self, pipeline_name: str, 
                             execution_id: Optional[str] = None) -> PipelineExecution:
        """Execute an ETL pipeline"""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        
        execution_id = execution_id or f"{pipeline_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        execution = PipelineExecution(
            execution_id=execution_id,
            pipeline_name=pipeline_name,
            status=PipelineStatus.RUNNING,
            start_time=datetime.utcnow(),
            execution_log=[]
        )
        
        self.executions[execution_id] = execution
        
        try:
            self.logger.info(f"Starting pipeline execution: {execution_id}")
            execution.execution_log.append(f"Pipeline {pipeline_name} started at {execution.start_time}")
            
            # Get pipeline steps
            steps = self.pipelines[pipeline_name]
            
            # Execute steps in dependency order
            for step in steps:
                if not step.enabled:
                    execution.execution_log.append(f"Skipping disabled step: {step.step_name}")
                    continue
                
                # Check dependencies
                if step.dependencies:
                    for dep in step.dependencies:
                        if not await self._is_step_completed(execution_id, dep):
                            raise Exception(f"Dependency {dep} not completed for step {step.step_id}")
                
                # Execute step
                await self._execute_step(execution, step)
            
            # Mark as completed
            execution.status = PipelineStatus.COMPLETED
            execution.end_time = datetime.utcnow()
            execution.execution_log.append(f"Pipeline completed successfully at {execution.end_time}")
            
            self.logger.info(f"Pipeline execution completed: {execution_id}")
            
        except Exception as e:
            execution.status = PipelineStatus.FAILED
            execution.end_time = datetime.utcnow()
            execution.error_message = str(e)
            execution.execution_log.append(f"Pipeline failed: {str(e)}")
            
            self.logger.error(f"Pipeline execution failed: {execution_id} - {str(e)}")
        
        return execution
    
    async def _execute_step(self, execution: PipelineExecution, step: PipelineStep):
        """Execute a single pipeline step"""
        try:
            execution.execution_log.append(f"Executing step: {step.step_name}")
            
            # Extract data
            source_data = await self._extract_data(step.source_query)
            execution.records_processed += len(source_data)
            
            # Transform data
            transformed_data = await self._transform_data(source_data, step)
            
            # Load data
            await self._load_data(transformed_data, step.target_table)
            
            execution.execution_log.append(f"Step completed: {step.step_name} - {len(transformed_data)} records processed")
            
        except Exception as e:
            execution.records_failed += 1
            execution.execution_log.append(f"Step failed: {step.step_name} - {str(e)}")
            raise
    
    async def _extract_data(self, query: str) -> List[Dict[str, Any]]:
        """Extract data from source"""
        try:
            return self.sql_service.execute_query(query)
        except Exception as e:
            self.logger.error(f"Error extracting data: {str(e)}")
            raise
    
    async def _transform_data(self, data: List[Dict[str, Any]], 
                            step: PipelineStep) -> List[Dict[str, Any]]:
        """Transform data according to step configuration"""
        if not data:
            return []
        
        df = pd.DataFrame(data)
        
        try:
            if step.transformation_type == TransformationType.CLEAN:
                df = await self._clean_data(df, step.transformation_config)
            elif step.transformation_type == TransformationType.ENRICH:
                df = await self._enrich_data(df, step.transformation_config)
            elif step.transformation_type == TransformationType.AGGREGATE:
                df = await self._aggregate_data(df, step.transformation_config)
            elif step.transformation_type == TransformationType.NORMALIZE:
                df = await self._normalize_data(df, step.transformation_config)
            elif step.transformation_type == TransformationType.VALIDATE:
                df = await self._validate_data(df, step.transformation_config)
            elif step.transformation_type == TransformationType.DEDUPLICATE:
                df = await self._deduplicate_data(df, step.transformation_config)
            
            return df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"Error transforming data: {str(e)}")
            raise
    
    async def _clean_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Clean data according to configuration"""
        # Clean string columns
        if "clean_columns" in config:
            for col in config["clean_columns"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
        
        # Validate required columns
        if "validate_required" in config:
            for col in config["validate_required"]:
                if col in df.columns:
                    df = df.dropna(subset=[col])
        
        # Convert data types
        if "data_types" in config:
            for col, dtype in config["data_types"].items():
                if col in df.columns:
                    try:
                        df[col] = df[col].astype(dtype)
                    except Exception as e:
                        self.logger.warning(f"Could not convert {col} to {dtype}: {str(e)}")
        
        return df
    
    async def _enrich_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Enrich data with additional columns"""
        if "add_columns" in config:
            for col_name, expression in config["add_columns"].items():
                # This is a simplified version - in production, you'd use a proper SQL expression parser
                if "CASE" in expression:
                    # Handle CASE statements
                    df[col_name] = self._evaluate_case_expression(df, expression)
                elif "SUBSTRING" in expression:
                    # Handle SUBSTRING functions
                    df[col_name] = self._evaluate_substring_expression(df, expression)
                else:
                    # Simple column reference
                    df[col_name] = expression
        
        return df
    
    async def _aggregate_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Aggregate data according to configuration"""
        if "group_by" in config and "aggregations" in config:
            group_cols = config["group_by"]
            agg_dict = config["aggregations"]
            
            # Convert aggregation functions
            agg_functions = {}
            for col, func in agg_dict.items():
                if func.upper() == "COUNT(*)":
                    agg_functions[col] = "count"
                elif func.upper().startswith("SUM("):
                    agg_functions[col] = "sum"
                elif func.upper().startswith("AVG("):
                    agg_functions[col] = "mean"
                elif func.upper().startswith("MIN("):
                    agg_functions[col] = "min"
                elif func.upper().startswith("MAX("):
                    agg_functions[col] = "max"
                elif func.upper().startswith("STDEV("):
                    agg_functions[col] = "std"
            
            # Perform aggregation
            if group_cols:
                df = df.groupby(group_cols).agg(agg_functions).reset_index()
            else:
                df = df.agg(agg_functions).to_frame().T
        
        return df
    
    async def _normalize_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Normalize data according to configuration"""
        method = config.get("normalization_method", "min_max")
        target_range = config.get("target_range", [0, 1])
        group_by = config.get("group_by", [])
        
        if group_by:
            # Normalize within groups
            for group, group_df in df.groupby(group_by):
                for col in df.columns:
                    if col not in group_by and df[col].dtype in ['int64', 'float64']:
                        if method == "min_max":
                            min_val = group_df[col].min()
                            max_val = group_df[col].max()
                            if max_val != min_val:
                                df.loc[group_df.index, col] = (group_df[col] - min_val) / (max_val - min_val)
        else:
            # Normalize entire dataset
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    if method == "min_max":
                        min_val = df[col].min()
                        max_val = df[col].max()
                        if max_val != min_val:
                            df[col] = (df[col] - min_val) / (max_val - min_val)
        
        return df
    
    async def _validate_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Validate data according to configuration"""
        # This would implement data validation rules
        # For now, just return the dataframe
        return df
    
    async def _deduplicate_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Remove duplicates according to configuration"""
        subset = config.get("subset", None)
        keep = config.get("keep", "first")
        
        if subset:
            df = df.drop_duplicates(subset=subset, keep=keep)
        else:
            df = df.drop_duplicates(keep=keep)
        
        return df
    
    async def _load_data(self, data: List[Dict[str, Any]], target_table: str):
        """Load transformed data to target table"""
        if not data:
            return
        
        try:
            # Create table if it doesn't exist
            await self._create_target_table(target_table, data[0].keys())
            
            # Insert data
            for record in data:
                self.sql_service.execute_non_query(
                    f"INSERT INTO {target_table} ({', '.join(record.keys())}) VALUES ({', '.join(['?' for _ in record.values()])})",
                    tuple(record.values())
                )
            
        except Exception as e:
            self.logger.error(f"Error loading data to {target_table}: {str(e)}")
            raise
    
    async def _create_target_table(self, table_name: str, columns: List[str]):
        """Create target table if it doesn't exist"""
        # This would create the table based on the data structure
        # For now, just log
        self.logger.info(f"Creating target table: {table_name} with columns: {columns}")
    
    async def _is_step_completed(self, execution_id: str, step_id: str) -> bool:
        """Check if a step is completed"""
        # This would check the execution log for step completion
        # For now, return True
        return True
    
    def _evaluate_case_expression(self, df: pd.DataFrame, expression: str) -> pd.Series:
        """Evaluate CASE expression (simplified)"""
        # This is a simplified implementation
        # In production, you'd use a proper SQL expression parser
        result = pd.Series(["other"] * len(df))
        
        if "document" in expression.lower():
            result = df.get("content_type", pd.Series()).str.contains("pdf", case=False, na=False)
        elif "image" in expression.lower():
            result = df.get("content_type", pd.Series()).str.contains("image", case=False, na=False)
        
        return result
    
    def _evaluate_substring_expression(self, df: pd.DataFrame, expression: str) -> pd.Series:
        """Evaluate SUBSTRING expression (simplified)"""
        # This is a simplified implementation
        # In production, you'd use a proper SQL expression parser
        if "file_name" in expression:
            return df.get("file_name", pd.Series()).str.split(".").str[-1]
        
        return pd.Series([""] * len(df))

# Pydantic models for API
class PipelineExecutionRequest(BaseModel):
    pipeline_name: str
    execution_id: Optional[str] = None

class PipelineStatusResponse(BaseModel):
    execution_id: str
    pipeline_name: str
    status: str
    start_time: str
    end_time: Optional[str]
    records_processed: int
    records_failed: int
    error_message: Optional[str]
    execution_log: List[str]

# Global ETL pipeline instance
etl_pipeline = ETLPipeline()