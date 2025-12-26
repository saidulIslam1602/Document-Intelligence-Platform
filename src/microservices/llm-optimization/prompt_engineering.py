"""
Advanced Prompt Engineering for Large Language Models
Enterprise-level prompt optimization for M365 Copilot features
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from azure.openai import AzureOpenAI
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
import openai
from transformers import AutoTokenizer, AutoModel
import torch

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import DomainEvent, EventType, EventBus

class PromptType(Enum):
    """Prompt type enumeration"""
    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    Q_A = "q_a"
    CODE_GENERATION = "code_generation"
    CREATIVE_WRITING = "creative_writing"

class PromptOptimizationStrategy(Enum):
    """Prompt optimization strategy enumeration"""
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    ROLE_PLAYING = "role_playing"
    TEMPLATE_BASED = "template_based"
    DYNAMIC = "dynamic"
    CONTEXT_AWARE = "context_aware"

@dataclass
class PromptTemplate:
    """Prompt template structure"""
    template_id: str
    name: str
    description: str
    prompt_type: PromptType
    template: str
    variables: List[str]
    examples: List[Dict[str, Any]]
    optimization_strategy: PromptOptimizationStrategy
    performance_metrics: Dict[str, float]
    created_at: datetime
    updated_at: datetime

@dataclass
class PromptEvaluation:
    """Prompt evaluation results"""
    template_id: str
    evaluation_id: str
    test_cases: List[Dict[str, Any]]
    metrics: Dict[str, float]
    feedback: List[str]
    recommendations: List[str]
    timestamp: datetime

class AdvancedPromptEngineering:
    """Advanced prompt engineering system for LLM optimization"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Azure OpenAI client
        self.openai_client = AzureOpenAI(
            api_key=self.config.openai_api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=self.config.openai_endpoint
        )
        
        # Prompt templates storage
        self.templates = {}
        self.evaluations = {}
        
        # Performance tracking
        self.performance_metrics = {}
        
        # Prompt optimization strategies
        self.optimization_strategies = {
            PromptOptimizationStrategy.FEW_SHOT: self._apply_few_shot_optimization,
            PromptOptimizationStrategy.CHAIN_OF_THOUGHT: self._apply_chain_of_thought_optimization,
            PromptOptimizationStrategy.ROLE_PLAYING: self._apply_role_playing_optimization,
            PromptOptimizationStrategy.TEMPLATE_BASED: self._apply_template_based_optimization,
            PromptOptimizationStrategy.DYNAMIC: self._apply_dynamic_optimization,
            PromptOptimizationStrategy.CONTEXT_AWARE: self._apply_context_aware_optimization
        }
    
    async def create_prompt_template(self, template: PromptTemplate) -> str:
        """Create a new prompt template"""
        try:
            # Validate template
            await self._validate_template(template)
            
            # Optimize template based on strategy
            optimized_template = await self._optimize_template(template)
            
            # Store template
            self.templates[template.template_id] = optimized_template
            
            # Initialize performance metrics
            self.performance_metrics[template.template_id] = {
                'total_requests': 0,
                'successful_requests': 0,
                'average_response_time': 0.0,
                'average_quality_score': 0.0,
                'user_satisfaction': 0.0
            }
            
            self.logger.info(f"Prompt template {template.template_id} created successfully")
            return template.template_id
            
        except Exception as e:
            self.logger.error(f"Error creating prompt template: {str(e)}")
            raise
    
    async def generate_response(self, template_id: str, variables: Dict[str, Any], 
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate response using prompt template"""
        try:
            # Get template
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Fill template with variables
            filled_prompt = await self._fill_template(template, variables, context)
            
            # Generate response
            start_time = datetime.utcnow()
            response = await self._generate_llm_response(filled_prompt, template)
            end_time = datetime.utcnow()
            
            # Calculate response time
            response_time = (end_time - start_time).total_seconds()
            
            # Evaluate response quality
            quality_score = await self._evaluate_response_quality(response, template, context)
            
            # Update performance metrics
            await self._update_performance_metrics(template_id, response_time, quality_score)
            
            return {
                'template_id': template_id,
                'prompt': filled_prompt,
                'response': response,
                'response_time': response_time,
                'quality_score': quality_score,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise
    
    async def optimize_prompt(self, template_id: str, 
                            optimization_data: Dict[str, Any]) -> PromptTemplate:
        """Optimize prompt template based on performance data"""
        try:
            # Get current template
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Analyze performance data
            performance_analysis = await self._analyze_performance_data(template_id, optimization_data)
            
            # Generate optimization suggestions
            optimization_suggestions = await self._generate_optimization_suggestions(
                template, performance_analysis
            )
            
            # Apply optimizations
            optimized_template = await self._apply_optimizations(
                template, optimization_suggestions
            )
            
            # Update template
            self.templates[template_id] = optimized_template
            
            self.logger.info(f"Prompt template {template_id} optimized successfully")
            return optimized_template
            
        except Exception as e:
            self.logger.error(f"Error optimizing prompt: {str(e)}")
            raise
    
    async def evaluate_prompt_performance(self, template_id: str, 
                                        test_cases: List[Dict[str, Any]]) -> PromptEvaluation:
        """Evaluate prompt performance with test cases"""
        try:
            # Get template
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Run test cases
            test_results = []
            for test_case in test_cases:
                result = await self.generate_response(
                    template_id, 
                    test_case['variables'], 
                    test_case.get('context')
                )
                test_results.append(result)
            
            # Calculate metrics
            metrics = await self._calculate_evaluation_metrics(test_results, test_cases)
            
            # Generate feedback and recommendations
            feedback = await self._generate_feedback(test_results, test_cases)
            recommendations = await self._generate_recommendations(template, metrics, feedback)
            
            # Create evaluation
            evaluation = PromptEvaluation(
                template_id=template_id,
                evaluation_id=f"eval_{template_id}_{datetime.utcnow().timestamp()}",
                test_cases=test_cases,
                metrics=metrics,
                feedback=feedback,
                recommendations=recommendations,
                timestamp=datetime.utcnow()
            )
            
            # Store evaluation
            self.evaluations[evaluation.evaluation_id] = evaluation
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Error evaluating prompt performance: {str(e)}")
            raise
    
    async def create_copilot_prompt(self, task_type: str, context: Dict[str, Any]) -> str:
        """Create Microsoft Copilot-style prompt for specific task"""
        try:
            # Define Copilot prompt templates for different tasks
            copilot_templates = {
                'document_summary': self._create_document_summary_prompt,
                'email_composition': self._create_email_composition_prompt,
                'meeting_notes': self._create_meeting_notes_prompt,
                'code_review': self._create_code_review_prompt,
                'presentation_outline': self._create_presentation_outline_prompt,
                'data_analysis': self._create_data_analysis_prompt,
                'translation': self._create_translation_prompt,
                'q_a': self._create_qa_prompt
            }
            
            if task_type not in copilot_templates:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            # Create task-specific prompt
            prompt = await copilot_templates[task_type](context)
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error creating Copilot prompt: {str(e)}")
            raise
    
    async def _validate_template(self, template: PromptTemplate):
        """Validate prompt template"""
        # Check required fields
        if not template.template_id or not template.template:
            raise ValueError("Template ID and template content are required")
        
        # Check template syntax
        if not self._validate_template_syntax(template.template):
            raise ValueError("Invalid template syntax")
        
        # Check variables match template
        template_variables = self._extract_template_variables(template.template)
        if set(template_variables) != set(template.variables):
            raise ValueError("Template variables don't match template content")
    
    def _validate_template_syntax(self, template: str) -> bool:
        """Validate template syntax"""
        try:
            # Check for balanced braces
            open_braces = template.count('{')
            close_braces = template.count('}')
            if open_braces != close_braces:
                return False
            
            # Check for valid variable names
            variable_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
            matches = re.findall(variable_pattern, template)
            for match in matches:
                if not match.isidentifier():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating template syntax: {str(e)}")
            return False
    
    def _extract_template_variables(self, template: str) -> List[str]:
        """Extract variables from template"""
        variable_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(variable_pattern, template)
        return list(set(matches))
    
    async def _optimize_template(self, template: PromptTemplate) -> PromptTemplate:
        """Optimize template based on strategy"""
        try:
            strategy = template.optimization_strategy
            if strategy in self.optimization_strategies:
                optimized_template = await self.optimization_strategies[strategy](template)
                return optimized_template
            else:
                return template
                
        except Exception as e:
            self.logger.error(f"Error optimizing template: {str(e)}")
            return template
    
    async def _apply_few_shot_optimization(self, template: PromptTemplate) -> PromptTemplate:
        """Apply few-shot learning optimization"""
        try:
            # Add few-shot examples to template
            if template.examples:
                examples_text = "\n\nExamples:\n"
                for i, example in enumerate(template.examples):
                    examples_text += f"Example {i+1}:\n"
                    examples_text += f"Input: {example.get('input', '')}\n"
                    examples_text += f"Output: {example.get('output', '')}\n\n"
                
                template.template = template.template + examples_text
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error applying few-shot optimization: {str(e)}")
            return template
    
    async def _apply_chain_of_thought_optimization(self, template: PromptTemplate) -> PromptTemplate:
        """Apply chain-of-thought optimization"""
        try:
            # Add chain-of-thought instructions
            cot_instruction = "\n\nPlease think step by step and explain your reasoning process."
            template.template = template.template + cot_instruction
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error applying chain-of-thought optimization: {str(e)}")
            return template
    
    async def _apply_role_playing_optimization(self, template: PromptTemplate) -> PromptTemplate:
        """Apply role-playing optimization"""
        try:
            # Add role-playing context
            role_instruction = "\n\nYou are an expert assistant with deep knowledge in this domain. Please provide professional, accurate, and helpful responses."
            template.template = template.template + role_instruction
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error applying role-playing optimization: {str(e)}")
            return template
    
    async def _apply_template_based_optimization(self, template: PromptTemplate) -> PromptTemplate:
        """Apply template-based optimization"""
        try:
            # Use structured template format
            structured_template = f"""
            Task: {template.description}
            
            Instructions:
            {template.template}
            
            Please follow the instructions carefully and provide a complete response.
            """
            
            template.template = structured_template
            return template
            
        except Exception as e:
            self.logger.error(f"Error applying template-based optimization: {str(e)}")
            return template
    
    async def _apply_dynamic_optimization(self, template: PromptTemplate) -> PromptTemplate:
        """Apply dynamic optimization based on context"""
        try:
            # Add dynamic context handling
            dynamic_instruction = "\n\nPlease adapt your response based on the provided context and user needs."
            template.template = template.template + dynamic_instruction
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error applying dynamic optimization: {str(e)}")
            return template
    
    async def _apply_context_aware_optimization(self, template: PromptTemplate) -> PromptTemplate:
        """Apply context-aware optimization"""
        try:
            # Add context awareness instructions
            context_instruction = "\n\nPlease consider the provided context and maintain consistency with previous interactions."
            template.template = template.template + context_instruction
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error applying context-aware optimization: {str(e)}")
            return template
    
    async def _fill_template(self, template: PromptTemplate, variables: Dict[str, Any], 
                           context: Dict[str, Any] = None) -> str:
        """Fill template with variables and context"""
        try:
            filled_template = template.template
            
            # Replace variables with proper validation and escaping
            for var_name, var_value in variables.items():
                # Validate variable name
                if not var_name or not isinstance(var_name, str):
                    raise ValueError(f"Invalid variable name: {var_name}")
                
                # Escape special characters in variable value
                escaped_value = self._escape_template_value(str(var_value))
                
                # Replace all occurrences of the placeholder
                placeholder = f"{{{var_name}}}"
                if placeholder in filled_template:
                    filled_template = filled_template.replace(placeholder, escaped_value)
                else:
                    self.logger.warning(f"Variable '{var_name}' not found in template")
            
            # Validate that all placeholders have been replaced
            remaining_placeholders = self._find_unreplaced_placeholders(filled_template)
            if remaining_placeholders:
                self.logger.warning(f"Unreplaced placeholders found: {remaining_placeholders}")
            
            # Add context if provided
            if context:
                context_text = "\n\nContext:\n"
                for key, value in context.items():
                    context_text += f"{key}: {value}\n"
                filled_template = filled_template + context_text
            
            return filled_template
            
        except Exception as e:
            self.logger.error(f"Error filling template: {str(e)}")
            raise
    
    def _escape_template_value(self, value: str) -> str:
        """Escape special characters in template values"""
        if not isinstance(value, str):
            value = str(value)
        
        # Escape common special characters that could break templates
        escaped_value = value.replace('\\', '\\\\')  # Escape backslashes
        escaped_value = escaped_value.replace('\n', '\\n')  # Escape newlines
        escaped_value = escaped_value.replace('\r', '\\r')  # Escape carriage returns
        escaped_value = escaped_value.replace('\t', '\\t')  # Escape tabs
        
        return escaped_value
    
    def _find_unreplaced_placeholders(self, template: str) -> List[str]:
        """Find unreplaced placeholders in template"""
        import re
        pattern = r'\{[^}]+\}'
        placeholders = re.findall(pattern, template)
        return list(set(placeholders))  # Remove duplicates
    
    async def _generate_llm_response(self, prompt: str, template: PromptTemplate) -> str:
        """Generate response using LLM"""
        try:
            # Use appropriate model based on prompt type
            if template.prompt_type == PromptType.CHAT:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
            else:
                response = await self.openai_client.completions.create(
                    model="gpt-3.5-turbo-instruct",
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].text
            
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {str(e)}")
            raise
    
    async def _evaluate_response_quality(self, response: str, template: PromptTemplate, 
                                       context: Dict[str, Any] = None) -> float:
        """Evaluate response quality"""
        try:
            # Basic quality metrics
            quality_score = 0.0
            
            # Length appropriateness
            if 50 <= len(response) <= 2000:
                quality_score += 0.2
            
            # Coherence (simple check)
            if self._check_coherence(response):
                quality_score += 0.3
            
            # Relevance to prompt type
            if self._check_relevance(response, template.prompt_type):
                quality_score += 0.3
            
            # Completeness
            if self._check_completeness(response, template):
                quality_score += 0.2
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error evaluating response quality: {str(e)}")
            return 0.0
    
    def _check_coherence(self, response: str) -> bool:
        """Check response coherence"""
        # Simple coherence check - in production, use more sophisticated methods
        sentences = response.split('.')
        return len(sentences) > 1 and all(len(sentence.strip()) > 10 for sentence in sentences[:-1])
    
    def _check_relevance(self, response: str, prompt_type: PromptType) -> bool:
        """Check response relevance to prompt type"""
        # Simple relevance check - in production, use more sophisticated methods
        if prompt_type == PromptType.SUMMARIZATION:
            return len(response) < 500  # Summaries should be concise
        elif prompt_type == PromptType.CODE_GENERATION:
            return any(keyword in response.lower() for keyword in ['def ', 'function', 'class ', 'import'])
        else:
            return True
    
    def _check_completeness(self, response: str, template: PromptTemplate) -> bool:
        """Check response completeness"""
        # Simple completeness check - in production, use more sophisticated methods
        return len(response) > 50 and not response.endswith('...')
    
    async def _update_performance_metrics(self, template_id: str, response_time: float, 
                                        quality_score: float):
        """Update performance metrics for template"""
        try:
            if template_id in self.performance_metrics:
                metrics = self.performance_metrics[template_id]
                metrics['total_requests'] += 1
                metrics['successful_requests'] += 1
                
                # Update average response time
                total_requests = metrics['total_requests']
                current_avg_time = metrics['average_response_time']
                metrics['average_response_time'] = (
                    (current_avg_time * (total_requests - 1) + response_time) / total_requests
                )
                
                # Update average quality score
                current_avg_quality = metrics['average_quality_score']
                metrics['average_quality_score'] = (
                    (current_avg_quality * (total_requests - 1) + quality_score) / total_requests
                )
                
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {str(e)}")
    
    # Microsoft Copilot-specific prompt templates
    async def _create_document_summary_prompt(self, context: Dict[str, Any]) -> str:
        """Create document summary prompt for Copilot"""
        return f"""
        Please provide a comprehensive summary of the following document:
        
        Document: {context.get('document_content', '')}
        
        Requirements:
        - Summarize the key points and main ideas
        - Highlight important details and insights
        - Maintain a professional tone
        - Keep the summary concise but informative
        - Include any action items or next steps if mentioned
        
        Please provide your summary below:
        """
    
    async def _create_email_composition_prompt(self, context: Dict[str, Any]) -> str:
        """Create email composition prompt for Copilot"""
        return f"""
        Please help compose an email with the following details:
        
        Recipient: {context.get('recipient', '')}
        Subject: {context.get('subject', '')}
        Purpose: {context.get('purpose', '')}
        Key Points: {context.get('key_points', '')}
        Tone: {context.get('tone', 'professional')}
        
        Please compose a well-structured email that:
        - Has a clear and engaging subject line
        - Includes a proper greeting and closing
        - Covers all the key points effectively
        - Maintains the specified tone
        - Is appropriate for the recipient and context
        
        Email:
        """
    
    async def _create_meeting_notes_prompt(self, context: Dict[str, Any]) -> str:
        """Create meeting notes prompt for Copilot"""
        return f"""
        Please help create comprehensive meeting notes from the following information:
        
        Meeting Details:
        - Date: {context.get('date', '')}
        - Attendees: {context.get('attendees', '')}
        - Duration: {context.get('duration', '')}
        - Main Topics: {context.get('topics', '')}
        
        Discussion Points: {context.get('discussion', '')}
        
        Please create meeting notes that include:
        - Meeting overview and attendees
        - Key discussion points and decisions
        - Action items with owners and deadlines
        - Next steps and follow-up items
        - Important insights or conclusions
        
        Meeting Notes:
        """
    
    async def _create_code_review_prompt(self, context: Dict[str, Any]) -> str:
        """Create code review prompt for Copilot"""
        return f"""
        Please review the following code and provide feedback:
        
        Code:
        {context.get('code', '')}
        
        Language: {context.get('language', '')}
        Purpose: {context.get('purpose', '')}
        
        Please provide a code review that includes:
        - Code quality assessment
        - Potential bugs or issues
        - Performance considerations
        - Best practices recommendations
        - Security considerations
        - Suggestions for improvement
        
        Code Review:
        """
    
    async def _create_presentation_outline_prompt(self, context: Dict[str, Any]) -> str:
        """Create presentation outline prompt for Copilot"""
        return f"""
        Please create a presentation outline for the following topic:
        
        Topic: {context.get('topic', '')}
        Audience: {context.get('audience', '')}
        Duration: {context.get('duration', '')}
        Key Messages: {context.get('key_messages', '')}
        
        Please create a presentation outline that includes:
        - Title slide
        - Introduction and agenda
        - Main content sections with key points
        - Supporting data or examples
        - Conclusion and call to action
        - Q&A section
        
        Presentation Outline:
        """
    
    async def _create_data_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Create data analysis prompt for Copilot"""
        return f"""
        Please analyze the following data and provide insights:
        
        Data: {context.get('data', '')}
        Analysis Type: {context.get('analysis_type', '')}
        Questions: {context.get('questions', '')}
        
        Please provide:
        - Data summary and key statistics
        - Trends and patterns identified
        - Insights and observations
        - Recommendations based on the data
        - Visualizations suggestions
        
        Data Analysis:
        """
    
    async def _create_translation_prompt(self, context: Dict[str, Any]) -> str:
        """Create translation prompt for Copilot"""
        return f"""
        Please translate the following text:
        
        Text: {context.get('text', '')}
        Source Language: {context.get('source_language', '')}
        Target Language: {context.get('target_language', '')}
        Context: {context.get('context', '')}
        
        Please provide:
        - Accurate translation
        - Cultural context considerations
        - Alternative translations if applicable
        - Notes on any ambiguous terms
        
        Translation:
        """
    
    async def _create_qa_prompt(self, context: Dict[str, Any]) -> str:
        """Create Q&A prompt for Copilot"""
        return f"""
        Please answer the following question based on the provided context:
        
        Question: {context.get('question', '')}
        Context: {context.get('context', '')}
        Domain: {context.get('domain', '')}
        
        Please provide:
        - Direct answer to the question
        - Supporting evidence from the context
        - Additional relevant information
        - Sources or references if applicable
        
        Answer:
        """
    
    # Additional helper methods would be implemented here
    # for performance analysis, optimization, etc.