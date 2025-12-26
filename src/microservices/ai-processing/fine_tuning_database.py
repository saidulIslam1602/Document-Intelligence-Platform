"""
Fine-Tuning Database Schema
Database tables and migrations for fine-tuning functionality
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from src.shared.storage.sql_service import SQLService
from src.shared.config.settings import config_manager

logger = logging.getLogger(__name__)

class FineTuningDatabase:
    """Database operations for fine-tuning functionality"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.sql_service = SQLService(self.config.sql_connection_string)
    
    async def create_tables(self):
        """Create fine-tuning related database tables"""
        try:
            # Fine-tuning jobs table
            jobs_table = """
            CREATE TABLE IF NOT EXISTS fine_tuning_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                training_file_id VARCHAR(255) NOT NULL,
                validation_file_id VARCHAR(255),
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                fine_tuned_model VARCHAR(255),
                hyperparameters TEXT,
                training_tokens INTEGER,
                error_message TEXT,
                created_by VARCHAR(100),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            # Fine-tuning workflows table
            workflows_table = """
            CREATE TABLE IF NOT EXISTS fine_tuning_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                document_type VARCHAR(100) NOT NULL,
                industry VARCHAR(100) NOT NULL,
                steps TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                metrics TEXT,
                created_by VARCHAR(100),
                target_accuracy FLOAT DEFAULT 0.85,
                max_training_time_hours INTEGER DEFAULT 24
            )
            """
            
            # Training data table
            training_data_table = """
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id VARCHAR(255) NOT NULL,
                document_id VARCHAR(255) NOT NULL,
                document_type VARCHAR(100) NOT NULL,
                industry VARCHAR(100) NOT NULL,
                extracted_text TEXT NOT NULL,
                entities TEXT,
                summary TEXT,
                confidence FLOAT,
                preprocessed_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES fine_tuning_workflows(workflow_id)
            )
            """
            
            # Model evaluations table
            evaluations_table = """
            CREATE TABLE IF NOT EXISTS model_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id VARCHAR(255) UNIQUE NOT NULL,
                model_name VARCHAR(255) NOT NULL,
                workflow_id VARCHAR(255),
                evaluation_type VARCHAR(50) NOT NULL,
                total_documents INTEGER NOT NULL,
                accuracy FLOAT NOT NULL,
                average_confidence FLOAT NOT NULL,
                document_type_accuracy TEXT,
                industry_accuracy TEXT,
                evaluation_metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                FOREIGN KEY (workflow_id) REFERENCES fine_tuning_workflows(workflow_id)
            )
            """
            
            # Model deployments table
            deployments_table = """
            CREATE TABLE IF NOT EXISTS model_deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id VARCHAR(255) UNIQUE NOT NULL,
                model_name VARCHAR(255) NOT NULL,
                deployment_name VARCHAR(255) NOT NULL,
                deployment_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                configuration TEXT,
                monitoring_enabled BOOLEAN DEFAULT TRUE
            )
            """
            
            # Training metrics table
            training_metrics_table = """
            CREATE TABLE IF NOT EXISTS training_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) NOT NULL,
                step INTEGER NOT NULL,
                train_loss FLOAT,
                train_mean_token_accuracy FLOAT,
                valid_loss FLOAT,
                validation_mean_token_accuracy FLOAT,
                full_valid_loss FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES fine_tuning_jobs(job_id)
            )
            """
            
            # Execute table creation
            await self.sql_service.execute_non_query(jobs_table)
            await self.sql_service.execute_non_query(workflows_table)
            await self.sql_service.execute_non_query(training_data_table)
            await self.sql_service.execute_non_query(evaluations_table)
            await self.sql_service.execute_non_query(deployments_table)
            await self.sql_service.execute_non_query(training_metrics_table)
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("Fine-tuning database tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating fine-tuning tables: {str(e)}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_fine_tuning_jobs_status ON fine_tuning_jobs(status)",
                "CREATE INDEX IF NOT EXISTS idx_fine_tuning_jobs_model ON fine_tuning_jobs(model_name)",
                "CREATE INDEX IF NOT EXISTS idx_fine_tuning_jobs_created_at ON fine_tuning_jobs(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_workflows_status ON fine_tuning_workflows(status)",
                "CREATE INDEX IF NOT EXISTS idx_workflows_document_type ON fine_tuning_workflows(document_type)",
                "CREATE INDEX IF NOT EXISTS idx_workflows_industry ON fine_tuning_workflows(industry)",
                "CREATE INDEX IF NOT EXISTS idx_training_data_workflow ON training_data(workflow_id)",
                "CREATE INDEX IF NOT EXISTS idx_training_data_document_type ON training_data(document_type)",
                "CREATE INDEX IF NOT EXISTS idx_evaluations_model ON model_evaluations(model_name)",
                "CREATE INDEX IF NOT EXISTS idx_deployments_model ON model_deployments(model_name)",
                "CREATE INDEX IF NOT EXISTS idx_training_metrics_job ON training_metrics(job_id)"
            ]
            
            for index_sql in indexes:
                await self.sql_service.execute_non_query(index_sql)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise
    
    async def store_training_metrics(self, job_id: str, metrics: Dict[str, Any]):
        """Store training metrics for a job"""
        try:
            query = """
            INSERT INTO training_metrics 
            (job_id, step, train_loss, train_mean_token_accuracy, valid_loss, 
             validation_mean_token_accuracy, full_valid_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                job_id,
                metrics.get('step', 0),
                metrics.get('train_loss'),
                metrics.get('train_mean_token_accuracy'),
                metrics.get('valid_loss'),
                metrics.get('validation_mean_token_accuracy'),
                metrics.get('full_valid_loss')
            )
            
            await self.sql_service.execute_non_query(query, params)
            
        except Exception as e:
            logger.error(f"Error storing training metrics: {str(e)}")
            raise
    
    async def get_training_metrics(self, job_id: str) -> List[Dict[str, Any]]:
        """Get training metrics for a job"""
        try:
            query = """
            SELECT step, train_loss, train_mean_token_accuracy, valid_loss,
                   validation_mean_token_accuracy, full_valid_loss, timestamp
            FROM training_metrics 
            WHERE job_id = ?
            ORDER BY step
            """
            
            result = await self.sql_service.execute_query(query, (job_id,))
            return result
            
        except Exception as e:
            logger.error(f"Error getting training metrics: {str(e)}")
            return []
    
    async def store_evaluation(self, evaluation_data: Dict[str, Any]):
        """Store model evaluation results"""
        try:
            query = """
            INSERT INTO model_evaluations 
            (evaluation_id, model_name, workflow_id, evaluation_type, total_documents,
             accuracy, average_confidence, document_type_accuracy, industry_accuracy,
             evaluation_metrics, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                evaluation_data.get('evaluation_id'),
                evaluation_data.get('model_name'),
                evaluation_data.get('workflow_id'),
                evaluation_data.get('evaluation_type', 'standard'),
                evaluation_data.get('total_documents'),
                evaluation_data.get('accuracy'),
                evaluation_data.get('average_confidence'),
                evaluation_data.get('document_type_accuracy', '{}'),
                evaluation_data.get('industry_accuracy', '{}'),
                evaluation_data.get('evaluation_metrics', '{}'),
                evaluation_data.get('created_by', 'system')
            )
            
            await self.sql_service.execute_non_query(query, params)
            
        except Exception as e:
            logger.error(f"Error storing evaluation: {str(e)}")
            raise
    
    async def get_evaluations(self, model_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get model evaluations"""
        try:
            if model_name:
                query = """
                SELECT * FROM model_evaluations 
                WHERE model_name = ?
                ORDER BY created_at DESC
                LIMIT ?
                """
                params = (model_name, limit)
            else:
                query = """
                SELECT * FROM model_evaluations 
                ORDER BY created_at DESC
                LIMIT ?
                """
                params = (limit,)
            
            result = await self.sql_service.execute_query(query, params)
            return result
            
        except Exception as e:
            logger.error(f"Error getting evaluations: {str(e)}")
            return []
    
    async def store_deployment(self, deployment_data: Dict[str, Any]):
        """Store model deployment information"""
        try:
            query = """
            INSERT INTO model_deployments 
            (deployment_id, model_name, deployment_name, deployment_type, status,
             created_by, configuration, monitoring_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                deployment_data.get('deployment_id'),
                deployment_data.get('model_name'),
                deployment_data.get('deployment_name'),
                deployment_data.get('deployment_type', 'standard'),
                deployment_data.get('status', 'active'),
                deployment_data.get('created_by', 'system'),
                deployment_data.get('configuration', '{}'),
                deployment_data.get('monitoring_enabled', True)
            )
            
            await self.sql_service.execute_non_query(query, params)
            
        except Exception as e:
            logger.error(f"Error storing deployment: {str(e)}")
            raise
    
    async def get_deployments(self, model_name: str = None) -> List[Dict[str, Any]]:
        """Get model deployments"""
        try:
            if model_name:
                query = """
                SELECT * FROM model_deployments 
                WHERE model_name = ?
                ORDER BY created_at DESC
                """
                params = (model_name,)
            else:
                query = """
                SELECT * FROM model_deployments 
                ORDER BY created_at DESC
                """
                params = ()
            
            result = await self.sql_service.execute_query(query, params)
            return result
            
        except Exception as e:
            logger.error(f"Error getting deployments: {str(e)}")
            return []
    
    async def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        try:
            # Total workflows
            total_query = "SELECT COUNT(*) as total FROM fine_tuning_workflows"
            total_result = await self.sql_service.execute_query(total_query)
            total_workflows = total_result[0]['total'] if total_result else 0
            
            # Completed workflows
            completed_query = "SELECT COUNT(*) as completed FROM fine_tuning_workflows WHERE status = 'completed'"
            completed_result = await self.sql_service.execute_query(completed_query)
            completed_workflows = completed_result[0]['completed'] if completed_result else 0
            
            # Failed workflows
            failed_query = "SELECT COUNT(*) as failed FROM fine_tuning_workflows WHERE status = 'failed'"
            failed_result = await self.sql_service.execute_query(failed_query)
            failed_workflows = failed_result[0]['failed'] if failed_result else 0
            
            # Average accuracy
            accuracy_query = """
            SELECT AVG(CAST(JSON_EXTRACT(metrics, '$.current_accuracy') AS FLOAT)) as avg_accuracy
            FROM fine_tuning_workflows 
            WHERE status = 'completed' AND metrics IS NOT NULL
            """
            accuracy_result = await self.sql_service.execute_query(accuracy_query)
            avg_accuracy = accuracy_result[0]['avg_accuracy'] if accuracy_result and accuracy_result[0]['avg_accuracy'] else 0.0
            
            return {
                "total_workflows": total_workflows,
                "completed_workflows": completed_workflows,
                "failed_workflows": failed_workflows,
                "success_rate": completed_workflows / total_workflows if total_workflows > 0 else 0.0,
                "average_accuracy": avg_accuracy
            }
            
        except Exception as e:
            logger.error(f"Error getting workflow statistics: {str(e)}")
            return {
                "total_workflows": 0,
                "completed_workflows": 0,
                "failed_workflows": 0,
                "success_rate": 0.0,
                "average_accuracy": 0.0
            }
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old training data and metrics"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clean up old training metrics
            metrics_query = """
            DELETE FROM training_metrics 
            WHERE timestamp < ?
            """
            await self.sql_service.execute_non_query(metrics_query, (cutoff_date,))
            
            # Clean up old evaluations
            evaluations_query = """
            DELETE FROM model_evaluations 
            WHERE created_at < ?
            """
            await self.sql_service.execute_non_query(evaluations_query, (cutoff_date,))
            
            logger.info(f"Cleaned up data older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
            raise

# Initialize database
async def initialize_fine_tuning_database():
    """Initialize fine-tuning database tables"""
    try:
        db = FineTuningDatabase()
        await db.create_tables()
        logger.info("Fine-tuning database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing fine-tuning database: {str(e)}")
        raise