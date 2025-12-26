"""
Advanced A/B Testing Framework for Document Intelligence Platform
Enterprise-level experimentation capabilities for M365 Copilot features
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
from scipy import stats
from scipy.stats import chi2_contingency, ttest_ind, mannwhitneyu
import plotly.graph_objects as go
import plotly.express as px
# Cosmos DB removed - using Azure SQL Database
from azure.monitor.query import MetricsQueryClient
from azure.identity import DefaultAzureCredential

from src.shared.config.settings import config_manager
from src.shared.events.event_sourcing import DomainEvent, EventType, EventBus

class ExperimentStatus(Enum):
    """Experiment status enumeration"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ExperimentType(Enum):
    """Experiment type enumeration"""
    A_B = "a_b"
    MULTI_VARIANT = "multi_variant"
    BANDIT = "bandit"
    SEQUENTIAL = "sequential"

class MetricType(Enum):
    """Metric type enumeration"""
    CONTINUOUS = "continuous"
    BINARY = "binary"
    COUNT = "count"
    RATIO = "ratio"

@dataclass
class ExperimentConfig:
    """Experiment configuration"""
    experiment_id: str
    name: str
    description: str
    experiment_type: ExperimentType
    status: ExperimentStatus
    start_date: datetime
    end_date: Optional[datetime]
    target_audience: Dict[str, Any]
    variants: List[Dict[str, Any]]
    primary_metrics: List[str]
    secondary_metrics: List[str]
    success_criteria: Dict[str, Any]
    traffic_allocation: Dict[str, float]
    min_sample_size: int
    max_sample_size: int
    confidence_level: float = 0.95
    power: float = 0.8
    mde: float = 0.05  # Minimum Detectable Effect

@dataclass
class ExperimentResult:
    """Experiment result"""
    experiment_id: str
    variant: str
    metric_name: str
    metric_value: float
    sample_size: int
    confidence_interval: Tuple[float, float]
    p_value: float
    is_significant: bool
    effect_size: float
    timestamp: datetime

class AdvancedABTestingFramework:
    """Advanced A/B testing framework for enterprise-level experimentation"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Azure clients
        # Cosmos DB removed - using Azure SQL Database for A/B testing data
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.metrics_client = MetricsQueryClient(DefaultAzureCredential())
        
        # A/B testing data stored in Azure SQL Database
        self._initialize_ab_testing_tables()
        # Event tracking through SQL Database
        
        # Active experiments cache
        self.active_experiments = {}
        
        # Statistical methods
        self.statistical_methods = {
            'continuous': self._analyze_continuous_metric,
            'binary': self._analyze_binary_metric,
            'count': self._analyze_count_metric,
            'ratio': self._analyze_ratio_metric
        }
    
    async def create_experiment(self, config: ExperimentConfig) -> str:
        """Create a new A/B test experiment"""
        try:
            # Validate experiment configuration
            await self._validate_experiment_config(config)
            
            # Calculate required sample size
            sample_size = await self._calculate_sample_size(config)
            config.min_sample_size = sample_size
            
            # Store experiment configuration
            experiment_doc = {
                'id': config.experiment_id,
                'name': config.name,
                'description': config.description,
                'experiment_type': config.experiment_type.value,
                'status': config.status.value,
                'start_date': config.start_date.isoformat(),
                'end_date': config.end_date.isoformat() if config.end_date else None,
                'target_audience': config.target_audience,
                'variants': config.variants,
                'primary_metrics': config.primary_metrics,
                'secondary_metrics': config.secondary_metrics,
                'success_criteria': config.success_criteria,
                'traffic_allocation': config.traffic_allocation,
                'min_sample_size': config.min_sample_size,
                'max_sample_size': config.max_sample_size,
                'confidence_level': config.confidence_level,
                'power': config.power,
                'mde': config.mde,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'partition_key': config.experiment_id
            }
            
            await self.experiments_container.create_item(experiment_doc)
            
            # Cache active experiment
            self.active_experiments[config.experiment_id] = config
            
            self.logger.info(f"Experiment {config.experiment_id} created successfully")
            return config.experiment_id
            
        except Exception as e:
            self.logger.error(f"Error creating experiment: {str(e)}")
            raise
    
    async def assign_user_to_variant(self, user_id: str, experiment_id: str, 
                                   context: Dict[str, Any] = None) -> str:
        """Assign user to experiment variant using consistent hashing"""
        try:
            # Get experiment configuration
            experiment = await self._get_experiment(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            # Check if user is eligible for experiment
            if not await self._is_user_eligible(user_id, experiment, context):
                return "control"
            
            # Use consistent hashing for assignment
            hash_input = f"{user_id}:{experiment_id}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            hash_ratio = hash_value / (2**32)
            
            # Assign to variant based on traffic allocation
            cumulative_allocation = 0
            for variant, allocation in experiment['traffic_allocation'].items():
                cumulative_allocation += allocation
                if hash_ratio <= cumulative_allocation:
                    # Log assignment
                    await self._log_user_assignment(user_id, experiment_id, variant, context)
                    return variant
            
            # Fallback to control
            return "control"
            
        except Exception as e:
            self.logger.error(f"Error assigning user to variant: {str(e)}")
            return "control"
    
    async def track_experiment_event(self, user_id: str, experiment_id: str, 
                                   event_name: str, event_data: Dict[str, Any] = None):
        """Track experiment event for analysis"""
        try:
            # Get user's variant assignment
            variant = await self._get_user_variant(user_id, experiment_id)
            if not variant:
                return
            
            # Create event record
            event_record = {
                'id': f"{user_id}:{experiment_id}:{event_name}:{datetime.utcnow().timestamp()}",
                'user_id': user_id,
                'experiment_id': experiment_id,
                'variant': variant,
                'event_name': event_name,
                'event_data': event_data or {},
                'timestamp': datetime.utcnow().isoformat(),
                'partition_key': experiment_id
            }
            
            await self.events_container.create_item(event_record)
            
            # Update real-time metrics
            await self._update_realtime_metrics(experiment_id, variant, event_name, event_data)
            
        except Exception as e:
            self.logger.error(f"Error tracking experiment event: {str(e)}")
    
    async def analyze_experiment(self, experiment_id: str, 
                               metrics: List[str] = None) -> Dict[str, Any]:
        """Analyze experiment results with advanced statistical methods"""
        try:
            # Get experiment configuration
            experiment = await self._get_experiment(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            # Get experiment data
            experiment_data = await self._get_experiment_data(experiment_id)
            
            # Analyze each metric
            analysis_results = {}
            for metric in metrics or experiment['primary_metrics']:
                metric_analysis = await self._analyze_metric(
                    experiment_id, metric, experiment_data
                )
                analysis_results[metric] = metric_analysis
            
            # Calculate overall experiment health
            health_score = await self._calculate_experiment_health(analysis_results)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(analysis_results, experiment)
            
            # Create comprehensive analysis report
            analysis_report = {
                'experiment_id': experiment_id,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'experiment_status': experiment['status'],
                'total_participants': len(experiment_data),
                'analysis_results': analysis_results,
                'health_score': health_score,
                'recommendations': recommendations,
                'statistical_power': await self._calculate_statistical_power(analysis_results),
                'confidence_intervals': await self._calculate_confidence_intervals(analysis_results)
            }
            
            # Store analysis results
            await self._store_analysis_results(analysis_report)
            
            return analysis_report
            
        except Exception as e:
            self.logger.error(f"Error analyzing experiment: {str(e)}")
            raise
    
    async def get_experiment_dashboard(self, experiment_id: str) -> Dict[str, Any]:
        """Get real-time experiment dashboard data"""
        try:
            # Get experiment configuration
            experiment = await self._get_experiment(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            # Get real-time metrics
            realtime_metrics = await self._get_realtime_metrics(experiment_id)
            
            # Get participant counts by variant
            participant_counts = await self._get_participant_counts(experiment_id)
            
            # Get conversion funnels
            conversion_funnels = await self._get_conversion_funnels(experiment_id)
            
            # Get statistical significance status
            significance_status = await self._get_significance_status(experiment_id)
            
            # Create dashboard data
            dashboard_data = {
                'experiment_id': experiment_id,
                'experiment_name': experiment['name'],
                'status': experiment['status'],
                'start_date': experiment['start_date'],
                'end_date': experiment['end_date'],
                'participant_counts': participant_counts,
                'realtime_metrics': realtime_metrics,
                'conversion_funnels': conversion_funnels,
                'significance_status': significance_status,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting experiment dashboard: {str(e)}")
            raise
    
    async def stop_experiment(self, experiment_id: str, reason: str = None) -> bool:
        """Stop experiment and finalize results"""
        try:
            # Update experiment status
            experiment = await self._get_experiment(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            experiment['status'] = ExperimentStatus.COMPLETED.value
            experiment['end_date'] = datetime.utcnow().isoformat()
            experiment['stop_reason'] = reason
            experiment['updated_at'] = datetime.utcnow().isoformat()
            
            await self.experiments_container.replace_item(
                item=experiment_id,
                body=experiment
            )
            
            # Run final analysis
            final_analysis = await self.analyze_experiment(experiment_id)
            
            # Generate final report
            final_report = await self._generate_final_report(experiment_id, final_analysis)
            
            # Store final report
            await self._store_final_report(final_report)
            
            # Remove from active experiments
            if experiment_id in self.active_experiments:
                del self.active_experiments[experiment_id]
            
            self.logger.info(f"Experiment {experiment_id} stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping experiment: {str(e)}")
            return False
    
    async def _validate_experiment_config(self, config: ExperimentConfig):
        """Validate experiment configuration"""
        # Validate traffic allocation sums to 1
        total_allocation = sum(config.traffic_allocation.values())
        if abs(total_allocation - 1.0) > 0.01:
            raise ValueError("Traffic allocation must sum to 1.0")
        
        # Validate variants
        if len(config.variants) < 2:
            raise ValueError("Experiment must have at least 2 variants")
        
        # Validate metrics
        if not config.primary_metrics:
            raise ValueError("Experiment must have at least one primary metric")
        
        # Validate sample size
        if config.min_sample_size <= 0:
            raise ValueError("Minimum sample size must be positive")
    
    async def _calculate_sample_size(self, config: ExperimentConfig) -> int:
        """Calculate required sample size for experiment"""
        try:
            # Use power analysis to calculate sample size
            # This is a simplified version - in production, use proper statistical libraries
            
            # For binary metrics
            if config.primary_metrics[0] in ['conversion_rate', 'click_rate', 'signup_rate']:
                # Use proportion test sample size calculation
                p1 = 0.1  # Baseline conversion rate
                p2 = p1 + config.mde  # Expected conversion rate
                alpha = 1 - config.confidence_level
                beta = 1 - config.power
                
                z_alpha = stats.norm.ppf(1 - alpha/2)
                z_beta = stats.norm.ppf(1 - beta)
                
                n = ((z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))) / ((p2 - p1) ** 2)
                return int(n * 2)  # Multiply by 2 for two groups
            
            # For continuous metrics
            else:
                # Use t-test sample size calculation
                effect_size = config.mde
                alpha = 1 - config.confidence_level
                beta = 1 - config.power
                
                z_alpha = stats.norm.ppf(1 - alpha/2)
                z_beta = stats.norm.ppf(1 - beta)
                
                n = (2 * (z_alpha + z_beta) ** 2) / (effect_size ** 2)
                return int(n)
                
        except Exception as e:
            self.logger.error(f"Error calculating sample size: {str(e)}")
            return 1000  # Default sample size
    
    async def _is_user_eligible(self, user_id: str, experiment: Dict[str, Any], 
                              context: Dict[str, Any] = None) -> bool:
        """Check if user is eligible for experiment"""
        try:
            # Check target audience criteria
            target_audience = experiment.get('target_audience', {})
            
            # Check user attributes
            if 'user_attributes' in target_audience:
                user_attrs = context.get('user_attributes', {}) if context else {}
                for attr, value in target_audience['user_attributes'].items():
                    if user_attrs.get(attr) != value:
                        return False
            
            # Check geographic criteria
            if 'geographic' in target_audience:
                user_location = context.get('location', '') if context else ''
                if user_location not in target_audience['geographic']:
                    return False
            
            # Check device criteria
            if 'device_types' in target_audience:
                user_device = context.get('device_type', '') if context else ''
                if user_device not in target_audience['device_types']:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking user eligibility: {str(e)}")
            return False
    
    async def _log_user_assignment(self, user_id: str, experiment_id: str, 
                                 variant: str, context: Dict[str, Any] = None):
        """Log user assignment to experiment variant"""
        try:
            assignment_record = {
                'id': f"{user_id}:{experiment_id}",
                'user_id': user_id,
                'experiment_id': experiment_id,
                'variant': variant,
                'assigned_at': datetime.utcnow().isoformat(),
                'context': context or {},
                'partition_key': experiment_id
            }
            
            await self.events_container.create_item(assignment_record)
            
        except Exception as e:
            self.logger.error(f"Error logging user assignment: {str(e)}")
    
    async def _get_user_variant(self, user_id: str, experiment_id: str) -> Optional[str]:
        """Get user's assigned variant for experiment"""
        try:
            query = f"""
                SELECT c.variant 
                FROM c 
                WHERE c.user_id = '{user_id}' 
                AND c.experiment_id = '{experiment_id}'
                AND c.assigned_at IS NOT NULL
            """
            
            results = list(self.events_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            if results:
                return results[0]['variant']
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting user variant: {str(e)}")
            return None
    
    async def _analyze_metric(self, experiment_id: str, metric_name: str, 
                            experiment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze specific metric for experiment"""
        try:
            # Group data by variant
            variant_data = {}
            for record in experiment_data:
                variant = record.get('variant', 'control')
                if variant not in variant_data:
                    variant_data[variant] = []
                variant_data[variant].append(record)
            
            # Analyze each variant
            variant_analyses = {}
            for variant, data in variant_data.items():
                metric_values = [record.get(metric_name, 0) for record in data]
                
                analysis = {
                    'sample_size': len(metric_values),
                    'mean': np.mean(metric_values),
                    'std': np.std(metric_values),
                    'median': np.median(metric_values),
                    'confidence_interval': self._calculate_confidence_interval(metric_values),
                    'p_value': None,
                    'effect_size': None,
                    'is_significant': False
                }
                
                variant_analyses[variant] = analysis
            
            # Compare variants
            if len(variant_analyses) >= 2:
                control_data = variant_data.get('control', [])
                treatment_data = variant_data.get('treatment', [])
                
                if control_data and treatment_data:
                    control_values = [record.get(metric_name, 0) for record in control_data]
                    treatment_values = [record.get(metric_name, 0) for record in treatment_data]
                    
                    # Perform statistical test
                    p_value = self._perform_statistical_test(control_values, treatment_values)
                    
                    # Calculate effect size
                    effect_size = self._calculate_effect_size(control_values, treatment_values)
                    
                    # Update analyses
                    for variant in variant_analyses:
                        variant_analyses[variant]['p_value'] = p_value
                        variant_analyses[variant]['effect_size'] = effect_size
                        variant_analyses[variant]['is_significant'] = p_value < 0.05
            
            return {
                'metric_name': metric_name,
                'variant_analyses': variant_analyses,
                'overall_p_value': min([analysis['p_value'] for analysis in variant_analyses.values() if analysis['p_value']]),
                'overall_effect_size': max([analysis['effect_size'] for analysis in variant_analyses.values() if analysis['effect_size']]),
                'is_significant': any([analysis['is_significant'] for analysis in variant_analyses.values()])
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing metric {metric_name}: {str(e)}")
            raise
    
    def _calculate_confidence_interval(self, values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for values"""
        try:
            mean = np.mean(values)
            std = np.std(values)
            n = len(values)
            
            # Calculate standard error
            se = std / np.sqrt(n)
            
            # Calculate critical value
            alpha = 1 - confidence
            critical_value = stats.t.ppf(1 - alpha/2, n - 1)
            
            # Calculate margin of error
            margin_error = critical_value * se
            
            return (mean - margin_error, mean + margin_error)
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence interval: {str(e)}")
            return (0, 0)
    
    def _perform_statistical_test(self, control_values: List[float], 
                                treatment_values: List[float]) -> float:
        """Perform statistical test between control and treatment"""
        try:
            # Use t-test for continuous variables
            if len(control_values) > 30 and len(treatment_values) > 30:
                # Use independent t-test
                t_stat, p_value = ttest_ind(control_values, treatment_values)
            else:
                # Use Mann-Whitney U test for small samples
                u_stat, p_value = mannwhitneyu(control_values, treatment_values)
            
            return p_value
            
        except Exception as e:
            self.logger.error(f"Error performing statistical test: {str(e)}")
            return 1.0
    
    def _calculate_effect_size(self, control_values: List[float], 
                             treatment_values: List[float]) -> float:
        """Calculate effect size (Cohen's d)"""
        try:
            control_mean = np.mean(control_values)
            treatment_mean = np.mean(treatment_values)
            
            # Pooled standard deviation
            control_std = np.std(control_values)
            treatment_std = np.std(treatment_values)
            pooled_std = np.sqrt(((len(control_values) - 1) * control_std**2 + 
                                (len(treatment_values) - 1) * treatment_std**2) / 
                               (len(control_values) + len(treatment_values) - 2))
            
            # Cohen's d
            effect_size = (treatment_mean - control_mean) / pooled_std
            
            return effect_size
            
        except Exception as e:
            self.logger.error(f"Error calculating effect size: {str(e)}")
            return 0.0
    
    # Additional helper methods would be implemented here
    # for experiment management, data collection, analysis, etc.