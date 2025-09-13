"""
PoC Generator Service
Generates Proof of Concept demonstrations for customers
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import uuid

from ...shared.config.settings import config_manager
from ...shared.storage.sql_service import SQLService

class PoCStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class IndustryType(Enum):
    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    EDUCATION = "education"
    GOVERNMENT = "government"
    TECHNOLOGY = "technology"

@dataclass
class PoCScenario:
    scenario_id: str
    name: str
    description: str
    industry: IndustryType
    duration_minutes: int
    complexity: str  # "basic", "intermediate", "advanced"
    prerequisites: List[str]
    steps: List[Dict[str, Any]]
    expected_outcomes: List[str]
    resources_required: List[str]

@dataclass
class PoCInstance:
    instance_id: str
    scenario_id: str
    customer_name: str
    customer_email: str
    status: PoCStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    current_step: int = 0
    total_steps: int = 0
    results: Dict[str, Any] = None

class PoCGenerator:
    """Generates and manages Proof of Concept demonstrations"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        self.sql_service = SQLService(self.config.sql_connection_string)
        
        # Initialize predefined scenarios
        self._initialize_scenarios()
    
    def _initialize_scenarios(self):
        """Initialize predefined PoC scenarios"""
        self.scenarios = {
            "document_intelligence_basic": PoCScenario(
                scenario_id="document_intelligence_basic",
                name="Document Intelligence - Basic",
                description="Demonstrate basic document processing capabilities",
                industry=IndustryType.TECHNOLOGY,
                duration_minutes=30,
                complexity="basic",
                prerequisites=[
                    "Azure subscription",
                    "Sample documents (PDF, Word, Excel)",
                    "Basic understanding of AI/ML concepts"
                ],
                steps=[
                    {
                        "step": 1,
                        "title": "Setup Environment",
                        "description": "Deploy the document intelligence platform",
                        "duration_minutes": 5,
                        "actions": [
                            "Deploy Azure resources",
                            "Configure environment variables",
                            "Start microservices"
                        ]
                    },
                    {
                        "step": 2,
                        "title": "Upload Documents",
                        "description": "Upload sample documents for processing",
                        "duration_minutes": 10,
                        "actions": [
                            "Access document upload interface",
                            "Upload PDF documents",
                            "Upload Word documents",
                            "Upload Excel spreadsheets"
                        ]
                    },
                    {
                        "step": 3,
                        "title": "AI Processing",
                        "description": "Process documents with AI services",
                        "duration_minutes": 10,
                        "actions": [
                            "Run Form Recognizer analysis",
                            "Extract text and entities",
                            "Generate document summaries",
                            "Classify document types"
                        ]
                    },
                    {
                        "step": 4,
                        "title": "View Results",
                        "description": "Review processing results and analytics",
                        "duration_minutes": 5,
                        "actions": [
                            "View extracted text",
                            "Review entity recognition",
                            "Check document classification",
                            "Analyze processing metrics"
                        ]
                    }
                ],
                expected_outcomes=[
                    "Understanding of document processing capabilities",
                    "Hands-on experience with AI services",
                    "Clear view of business value proposition"
                ],
                resources_required=[
                    "Azure OpenAI service",
                    "Azure Form Recognizer",
                    "Azure Blob Storage",
                    "Sample documents"
                ]
            ),
            "data_migration_enterprise": PoCScenario(
                scenario_id="data_migration_enterprise",
                name="Enterprise Data Migration",
                description="Demonstrate migration from legacy systems to Azure",
                industry=IndustryType.FINANCIAL_SERVICES,
                duration_minutes=60,
                complexity="advanced",
                prerequisites=[
                    "Legacy database access (Teradata/Netezza)",
                    "Azure subscription with appropriate permissions",
                    "Understanding of data migration concepts"
                ],
                steps=[
                    {
                        "step": 1,
                        "title": "Assessment",
                        "description": "Analyze source database schema",
                        "duration_minutes": 15,
                        "actions": [
                            "Connect to source database",
                            "Analyze table structures",
                            "Identify data types and constraints",
                            "Calculate migration complexity"
                        ]
                    },
                    {
                        "step": 2,
                        "title": "Schema Conversion",
                        "description": "Convert legacy schema to Azure SQL",
                        "duration_minutes": 20,
                        "actions": [
                            "Convert DDL statements",
                            "Map data types",
                            "Handle constraints and indexes",
                            "Validate converted schema"
                        ]
                    },
                    {
                        "step": 3,
                        "title": "Data Migration",
                        "description": "Migrate data in batches",
                        "duration_minutes": 20,
                        "actions": [
                            "Create target tables",
                            "Migrate data in batches",
                            "Validate data integrity",
                            "Handle errors and retries"
                        ]
                    },
                    {
                        "step": 4,
                        "title": "Validation",
                        "description": "Validate migration results",
                        "duration_minutes": 5,
                        "actions": [
                            "Compare row counts",
                            "Validate data accuracy",
                            "Test query performance",
                            "Generate migration report"
                        ]
                    }
                ],
                expected_outcomes=[
                    "Complete understanding of migration process",
                    "Hands-on experience with migration tools",
                    "Clear migration timeline and cost estimates"
                ],
                resources_required=[
                    "Teradata/Netezza database",
                    "Azure SQL Database",
                    "Migration tools",
                    "Sample data"
                ]
            ),
            "fabric_analytics_demo": PoCScenario(
                scenario_id="fabric_analytics_demo",
                name="Microsoft Fabric Analytics",
                description="Demonstrate Microsoft Fabric capabilities",
                industry=IndustryType.RETAIL,
                duration_minutes=45,
                complexity="intermediate",
                prerequisites=[
                    "Microsoft Fabric workspace",
                    "Sample retail data",
                    "Understanding of data analytics"
                ],
                steps=[
                    {
                        "step": 1,
                        "title": "OneLake Setup",
                        "description": "Create and configure OneLake",
                        "duration_minutes": 10,
                        "actions": [
                            "Create lakehouse",
                            "Upload sample data",
                            "Configure data formats",
                            "Set up shortcuts"
                        ]
                    },
                    {
                        "step": 2,
                        "title": "Data Warehouse",
                        "description": "Create and query data warehouse",
                        "duration_minutes": 15,
                        "actions": [
                            "Create warehouse",
                            "Load data from OneLake",
                            "Create tables and views",
                            "Execute sample queries"
                        ]
                    },
                    {
                        "step": 3,
                        "title": "Real-time Intelligence",
                        "description": "Set up real-time analytics",
                        "duration_minutes": 15,
                        "actions": [
                            "Configure event streaming",
                            "Create KQL queries",
                            "Set up real-time dashboards",
                            "Monitor live data"
                        ]
                    },
                    {
                        "step": 4,
                        "title": "Power BI Integration",
                        "description": "Create Power BI reports",
                        "duration_minutes": 5,
                        "actions": [
                            "Connect to Fabric data",
                            "Create sample reports",
                            "Set up auto-refresh",
                            "Share reports"
                        ]
                    }
                ],
                expected_outcomes=[
                    "Understanding of Fabric capabilities",
                    "Hands-on experience with OneLake",
                    "Clear view of analytics potential"
                ],
                resources_required=[
                    "Microsoft Fabric workspace",
                    "Power BI Pro license",
                    "Sample retail data",
                    "KQL knowledge"
                ]
            )
        }
    
    async def create_poc_instance(self, scenario_id: str, customer_name: str, 
                                 customer_email: str) -> PoCInstance:
        """Create a new PoC instance"""
        try:
            if scenario_id not in self.scenarios:
                raise ValueError(f"Scenario '{scenario_id}' not found")
            
            scenario = self.scenarios[scenario_id]
            
            instance = PoCInstance(
                instance_id=str(uuid.uuid4()),
                scenario_id=scenario_id,
                customer_name=customer_name,
                customer_email=customer_email,
                status=PoCStatus.DRAFT,
                created_at=datetime.now(),
                total_steps=len(scenario.steps)
            )
            
            # Store in database
            await self._store_poc_instance(instance)
            
            self.logger.info(f"Created PoC instance: {instance.instance_id}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Error creating PoC instance: {str(e)}")
            raise
    
    async def start_poc(self, instance_id: str) -> Dict[str, Any]:
        """Start a PoC instance"""
        try:
            instance = await self._get_poc_instance(instance_id)
            if not instance:
                raise ValueError(f"PoC instance '{instance_id}' not found")
            
            # Update status
            instance.status = PoCStatus.ACTIVE
            instance.started_at = datetime.now()
            instance.progress_percentage = 0.0
            instance.current_step = 0
            
            await self._update_poc_instance(instance)
            
            # Initialize PoC environment
            await self._initialize_poc_environment(instance)
            
            return {
                "instance_id": instance_id,
                "status": "started",
                "started_at": instance.started_at.isoformat(),
                "next_step": 1,
                "total_steps": instance.total_steps
            }
            
        except Exception as e:
            self.logger.error(f"Error starting PoC: {str(e)}")
            raise
    
    async def execute_poc_step(self, instance_id: str, step_number: int) -> Dict[str, Any]:
        """Execute a specific step in the PoC"""
        try:
            instance = await self._get_poc_instance(instance_id)
            if not instance:
                raise ValueError(f"PoC instance '{instance_id}' not found")
            
            scenario = self.scenarios[instance.scenario_id]
            step = scenario.steps[step_number - 1]
            
            # Execute step actions
            step_results = await self._execute_step_actions(instance, step)
            
            # Update progress
            instance.current_step = step_number
            instance.progress_percentage = (step_number / instance.total_steps) * 100
            
            if step_number == instance.total_steps:
                instance.status = PoCStatus.COMPLETED
                instance.completed_at = datetime.now()
            
            await self._update_poc_instance(instance)
            
            return {
                "instance_id": instance_id,
                "step": step_number,
                "title": step["title"],
                "results": step_results,
                "progress_percentage": instance.progress_percentage,
                "status": instance.status.value
            }
            
        except Exception as e:
            self.logger.error(f"Error executing PoC step: {str(e)}")
            raise
    
    async def _execute_step_actions(self, instance: PoCInstance, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute actions for a PoC step"""
        results = {
            "step_title": step["title"],
            "actions_completed": [],
            "actions_failed": [],
            "metrics": {},
            "duration_seconds": 0
        }
        
        start_time = datetime.now()
        
        try:
            for action in step["actions"]:
                # Simulate action execution
                await asyncio.sleep(1)  # Simulate processing time
                
                # In a real implementation, this would execute actual actions
                results["actions_completed"].append(action)
            
            end_time = datetime.now()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Generate mock metrics
            results["metrics"] = {
                "documents_processed": 10,
                "processing_time_ms": 2500,
                "accuracy_percentage": 95.5,
                "cost_usd": 0.15
            }
            
        except Exception as e:
            results["actions_failed"].append(f"Error: {str(e)}")
        
        return results
    
    async def get_poc_progress(self, instance_id: str) -> Dict[str, Any]:
        """Get PoC progress information"""
        try:
            instance = await self._get_poc_instance(instance_id)
            if not instance:
                raise ValueError(f"PoC instance '{instance_id}' not found")
            
            scenario = self.scenarios[instance.scenario_id]
            
            return {
                "instance_id": instance_id,
                "scenario_name": scenario.name,
                "customer_name": instance.customer_name,
                "status": instance.status.value,
                "progress_percentage": instance.progress_percentage,
                "current_step": instance.current_step,
                "total_steps": instance.total_steps,
                "created_at": instance.created_at.isoformat(),
                "started_at": instance.started_at.isoformat() if instance.started_at else None,
                "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
                "estimated_remaining_minutes": self._calculate_remaining_time(instance, scenario)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting PoC progress: {str(e)}")
            raise
    
    def _calculate_remaining_time(self, instance: PoCInstance, scenario: PoCScenario) -> int:
        """Calculate estimated remaining time for PoC"""
        if instance.status == PoCStatus.COMPLETED:
            return 0
        
        remaining_steps = instance.total_steps - instance.current_step
        total_remaining_minutes = 0
        
        for i in range(instance.current_step, instance.total_steps):
            total_remaining_minutes += scenario.steps[i]["duration_minutes"]
        
        return total_remaining_minutes
    
    async def generate_poc_report(self, instance_id: str) -> Dict[str, Any]:
        """Generate a comprehensive PoC report"""
        try:
            instance = await self._get_poc_instance(instance_id)
            if not instance:
                raise ValueError(f"PoC instance '{instance_id}' not found")
            
            scenario = self.scenarios[instance.scenario_id]
            
            report = {
                "instance_id": instance_id,
                "scenario": {
                    "name": scenario.name,
                    "description": scenario.description,
                    "industry": scenario.industry.value,
                    "complexity": scenario.complexity
                },
                "customer": {
                    "name": instance.customer_name,
                    "email": instance.customer_email
                },
                "execution": {
                    "status": instance.status.value,
                    "created_at": instance.created_at.isoformat(),
                    "started_at": instance.started_at.isoformat() if instance.started_at else None,
                    "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
                    "total_duration_minutes": self._calculate_total_duration(instance),
                    "progress_percentage": instance.progress_percentage
                },
                "results": {
                    "steps_completed": instance.current_step,
                    "total_steps": instance.total_steps,
                    "success_rate": (instance.current_step / instance.total_steps) * 100 if instance.total_steps > 0 else 0
                },
                "recommendations": self._generate_recommendations(instance, scenario),
                "next_steps": self._generate_next_steps(instance, scenario)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating PoC report: {str(e)}")
            raise
    
    def _calculate_total_duration(self, instance: PoCInstance) -> int:
        """Calculate total duration of PoC execution"""
        if not instance.started_at:
            return 0
        
        end_time = instance.completed_at or datetime.now()
        duration = end_time - instance.started_at
        return int(duration.total_seconds() / 60)
    
    def _generate_recommendations(self, instance: PoCInstance, scenario: PoCScenario) -> List[str]:
        """Generate recommendations based on PoC results"""
        recommendations = []
        
        if instance.status == PoCStatus.COMPLETED:
            recommendations.extend([
                "PoC completed successfully - ready for production planning",
                "Consider full-scale implementation based on demonstrated value",
                "Schedule follow-up meeting to discuss next steps"
            ])
        elif instance.progress_percentage > 50:
            recommendations.extend([
                "PoC is progressing well - continue with remaining steps",
                "Consider extending PoC duration for more comprehensive testing",
                "Document any challenges encountered for future reference"
            ])
        else:
            recommendations.extend([
                "PoC is in early stages - focus on completing initial steps",
                "Ensure all prerequisites are met before proceeding",
                "Consider additional training or support if needed"
            ])
        
        return recommendations
    
    def _generate_next_steps(self, instance: PoCInstance, scenario: PoCScenario) -> List[str]:
        """Generate next steps based on PoC status"""
        next_steps = []
        
        if instance.status == PoCStatus.COMPLETED:
            next_steps.extend([
                "Schedule production planning meeting",
                "Prepare detailed implementation proposal",
                "Identify key stakeholders for decision making"
            ])
        elif instance.status == PoCStatus.ACTIVE:
            next_steps.extend([
                f"Complete step {instance.current_step + 1} of {instance.total_steps}",
                "Review results from completed steps",
                "Address any issues or questions"
            ])
        else:
            next_steps.extend([
                "Start the PoC when ready",
                "Ensure all prerequisites are met",
                "Schedule dedicated time for PoC execution"
            ])
        
        return next_steps
    
    async def _store_poc_instance(self, instance: PoCInstance):
        """Store PoC instance in database"""
        # In a real implementation, this would store in SQL Database
        pass
    
    async def _get_poc_instance(self, instance_id: str) -> Optional[PoCInstance]:
        """Get PoC instance from database"""
        # In a real implementation, this would query SQL Database
        # For now, return None to indicate not found
        return None
    
    async def _update_poc_instance(self, instance: PoCInstance):
        """Update PoC instance in database"""
        # In a real implementation, this would update SQL Database
        pass
    
    async def _initialize_poc_environment(self, instance: PoCInstance):
        """Initialize environment for PoC execution"""
        # In a real implementation, this would set up the actual environment
        self.logger.info(f"Initializing PoC environment for instance: {instance.instance_id}")
    
    async def list_available_scenarios(self) -> List[Dict[str, Any]]:
        """List all available PoC scenarios"""
        scenarios = []
        for scenario in self.scenarios.values():
            scenarios.append({
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "description": scenario.description,
                "industry": scenario.industry.value,
                "duration_minutes": scenario.duration_minutes,
                "complexity": scenario.complexity,
                "prerequisites": scenario.prerequisites
            })
        
        return scenarios