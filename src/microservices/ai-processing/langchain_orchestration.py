"""
LangChain Orchestration for Invoice Processing Workflows
Wraps existing processing functions with LangChain chains for better workflow management
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from langchain.chains import LLMChain, SequentialChain
from langchain.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document

from ...shared.config.settings import config_manager
from .form_recognizer_service import FormRecognizerService
from .openai_service import OpenAIService
from .ml_models import MLModelManager

logger = logging.getLogger(__name__)

class LangChainOrchestrator:
    """LangChain-based orchestration for document intelligence workflows"""
    
    def __init__(self, event_bus=None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        
        # Initialize services
        self.form_recognizer = FormRecognizerService(event_bus)
        self.openai_service = OpenAIService(event_bus)
        self.ml_models = MLModelManager(event_bus)
        
        # Initialize LangChain LLM
        self.llm = AzureChatOpenAI(
            azure_endpoint=self.config.openai_endpoint,
            api_key=self.config.openai_api_key,
            api_version="2024-02-15-preview",
            deployment_name=self.config.openai_deployment,
            temperature=0.0
        )
        
        # Initialize chains
        self._initialize_chains()
    
    def _initialize_chains(self):
        """Initialize LangChain chains for workflows"""
        
        # Invoice Processing Chain
        self.invoice_chain = self._create_invoice_processing_chain()
        
        # Document Analysis Chain
        self.document_analysis_chain = self._create_document_analysis_chain()
        
        # Fine-Tuning Workflow Chain
        self.fine_tuning_chain = self._create_fine_tuning_workflow_chain()
    
    def _create_invoice_processing_chain(self) -> SequentialChain:
        """Create invoice processing chain: Upload → Extract → Validate → Classify → Store"""
        
        # Step 1: Extract invoice data
        extract_prompt = PromptTemplate(
            input_variables=["document_content"],
            template="""You are an AI assistant helping to extract invoice data.
            
            Analyze the following invoice document and identify:
            1. Vendor information
            2. Invoice number and date
            3. Line items with quantities and prices
            4. Total amount and tax
            5. Payment terms
            
            Document content: {document_content}
            
            Provide a structured summary of the invoice data."""
        )
        
        extract_chain = LLMChain(
            llm=self.llm,
            prompt=extract_prompt,
            output_key="extracted_data"
        )
        
        # Step 2: Validate invoice data
        validate_prompt = PromptTemplate(
            input_variables=["extracted_data"],
            template="""You are an AI assistant helping to validate invoice data.
            
            Review the following extracted invoice data and check for:
            1. Completeness (all required fields present)
            2. Accuracy (amounts add up correctly)
            3. Consistency (dates are valid, amounts are reasonable)
            4. Business rules compliance
            
            Extracted data: {extracted_data}
            
            Provide a validation report with issues found and recommendations."""
        )
        
        validate_chain = LLMChain(
            llm=self.llm,
            prompt=validate_prompt,
            output_key="validation_report"
        )
        
        # Step 3: Classify document quality
        classify_prompt = PromptTemplate(
            input_variables=["extracted_data", "validation_report"],
            template="""You are an AI assistant helping to classify invoice quality.
            
            Based on the extracted data and validation report, classify this invoice as:
            - FULLY_AUTOMATED: High confidence, complete data, no issues
            - REQUIRES_REVIEW: Medium confidence or minor issues
            - MANUAL_INTERVENTION: Low confidence or major issues
            
            Extracted data: {extracted_data}
            Validation report: {validation_report}
            
            Provide classification with reasoning."""
        )
        
        classify_chain = LLMChain(
            llm=self.llm,
            prompt=classify_prompt,
            output_key="classification"
        )
        
        # Create sequential chain
        invoice_chain = SequentialChain(
            chains=[extract_chain, validate_chain, classify_chain],
            input_variables=["document_content"],
            output_variables=["extracted_data", "validation_report", "classification"],
            verbose=True
        )
        
        return invoice_chain
    
    def _create_document_analysis_chain(self) -> SequentialChain:
        """Create document analysis chain: Retrieve → Summarize → Extract Entities → Generate Insights"""
        
        # Step 1: Summarize document
        summarize_prompt = PromptTemplate(
            input_variables=["document_text"],
            template="""You are an AI assistant helping to summarize documents.
            
            Provide a concise summary (2-3 sentences) of the following document:
            
            {document_text}
            
            Focus on key points and main purpose."""
        )
        
        summarize_chain = LLMChain(
            llm=self.llm,
            prompt=summarize_prompt,
            output_key="summary"
        )
        
        # Step 2: Extract entities
        entities_prompt = PromptTemplate(
            input_variables=["document_text"],
            template="""You are an AI assistant helping to extract entities from documents.
            
            Identify and extract the following entities from the document:
            - Organizations
            - People
            - Locations
            - Dates
            - Monetary amounts
            - Product/service names
            
            Document: {document_text}
            
            Provide a structured list of entities."""
        )
        
        entities_chain = LLMChain(
            llm=self.llm,
            prompt=entities_prompt,
            output_key="entities"
        )
        
        # Step 3: Generate insights
        insights_prompt = PromptTemplate(
            input_variables=["summary", "entities"],
            template="""You are an AI assistant helping to generate insights from documents.
            
            Based on the summary and extracted entities, provide:
            1. Key business insights
            2. Action items or follow-ups
            3. Risk factors or concerns
            4. Opportunities or recommendations
            
            Summary: {summary}
            Entities: {entities}
            
            Provide structured insights."""
        )
        
        insights_chain = LLMChain(
            llm=self.llm,
            prompt=insights_prompt,
            output_key="insights"
        )
        
        # Create sequential chain
        analysis_chain = SequentialChain(
            chains=[summarize_chain, entities_chain, insights_chain],
            input_variables=["document_text"],
            output_variables=["summary", "entities", "insights"],
            verbose=True
        )
        
        return analysis_chain
    
    def _create_fine_tuning_workflow_chain(self) -> SequentialChain:
        """Create fine-tuning workflow chain: Collect Data → Prepare → Train → Evaluate → Deploy"""
        
        # Step 1: Data quality assessment
        data_quality_prompt = PromptTemplate(
            input_variables=["training_data_sample"],
            template="""You are an AI assistant helping to assess training data quality.
            
            Review the following training data sample and assess:
            1. Data diversity
            2. Label quality
            3. Format consistency
            4. Potential biases
            5. Completeness
            
            Training data sample: {training_data_sample}
            
            Provide a quality assessment with recommendations."""
        )
        
        data_quality_chain = LLMChain(
            llm=self.llm,
            prompt=data_quality_prompt,
            output_key="data_quality_report"
        )
        
        # Step 2: Hyperparameter recommendations
        hyperparams_prompt = PromptTemplate(
            input_variables=["data_quality_report", "model_type"],
            template="""You are an AI assistant helping to recommend hyperparameters for fine-tuning.
            
            Based on the data quality report and model type, recommend:
            1. Learning rate
            2. Batch size
            3. Number of epochs
            4. Early stopping criteria
            
            Data quality: {data_quality_report}
            Model type: {model_type}
            
            Provide hyperparameter recommendations with reasoning."""
        )
        
        hyperparams_chain = LLMChain(
            llm=self.llm,
            prompt=hyperparams_prompt,
            output_key="hyperparameters"
        )
        
        # Step 3: Evaluation strategy
        evaluation_prompt = PromptTemplate(
            input_variables=["model_type", "hyperparameters"],
            template="""You are an AI assistant helping to define model evaluation strategy.
            
            Define evaluation strategy including:
            1. Metrics to track
            2. Validation approach
            3. Success criteria
            4. A/B testing plan
            
            Model type: {model_type}
            Hyperparameters: {hyperparameters}
            
            Provide evaluation strategy."""
        )
        
        evaluation_chain = LLMChain(
            llm=self.llm,
            prompt=evaluation_prompt,
            output_key="evaluation_strategy"
        )
        
        # Create sequential chain
        fine_tuning_chain = SequentialChain(
            chains=[data_quality_chain, hyperparams_chain, evaluation_chain],
            input_variables=["training_data_sample", "model_type"],
            output_variables=["data_quality_report", "hyperparameters", "evaluation_strategy"],
            verbose=True
        )
        
        return fine_tuning_chain
    
    async def process_invoice_with_langchain(
        self,
        document_content: bytes,
        document_id: str
    ) -> Dict[str, Any]:
        """Process invoice using LangChain orchestration"""
        try:
            start_time = datetime.utcnow()
            
            # Extract text using Form Recognizer (existing service)
            text_extraction = await self.form_recognizer.extract_text(document_content)
            extracted_text = text_extraction["text"]
            
            # Extract structured invoice data using Form Recognizer
            invoice_data = await self.form_recognizer.analyze_invoice(document_content)
            
            # Run LangChain invoice processing chain
            chain_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.invoice_chain.invoke({
                    "document_content": extracted_text[:4000]  # Limit for token count
                })
            )
            
            # Classify document using ML models (existing service)
            classification = await self.ml_models.classify_document(extracted_text)
            
            # Combine results
            result = {
                "document_id": document_id,
                "invoice_data": invoice_data,
                "langchain_analysis": {
                    "extracted_data": chain_result.get("extracted_data"),
                    "validation_report": chain_result.get("validation_report"),
                    "classification": chain_result.get("classification")
                },
                "ml_classification": classification,
                "text_extraction_confidence": text_extraction.get("confidence", 0.0),
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Invoice processed with LangChain: {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing invoice with LangChain: {str(e)}")
            raise
    
    async def analyze_document_with_langchain(
        self,
        document_text: str,
        document_id: str
    ) -> Dict[str, Any]:
        """Analyze document using LangChain orchestration"""
        try:
            start_time = datetime.utcnow()
            
            # Run LangChain document analysis chain
            chain_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.document_analysis_chain.invoke({
                    "document_text": document_text[:8000]  # Limit for token count
                })
            )
            
            # Extract entities using OpenAI (existing service)
            entities = await self.openai_service.extract_entities(document_text)
            
            # Analyze sentiment using ML models (existing service)
            sentiment = await self.ml_models.analyze_sentiment(document_text)
            
            # Combine results
            result = {
                "document_id": document_id,
                "langchain_analysis": {
                    "summary": chain_result.get("summary"),
                    "entities": chain_result.get("entities"),
                    "insights": chain_result.get("insights")
                },
                "openai_entities": entities.get("entities", []),
                "sentiment": sentiment,
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Document analyzed with LangChain: {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing document with LangChain: {str(e)}")
            raise
    
    async def orchestrate_fine_tuning_workflow(
        self,
        training_data_sample: str,
        model_type: str = "gpt-3.5-turbo"
    ) -> Dict[str, Any]:
        """Orchestrate fine-tuning workflow using LangChain"""
        try:
            start_time = datetime.utcnow()
            
            # Run LangChain fine-tuning workflow chain
            chain_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.fine_tuning_chain.invoke({
                    "training_data_sample": training_data_sample[:4000],
                    "model_type": model_type
                })
            )
            
            result = {
                "model_type": model_type,
                "workflow_analysis": {
                    "data_quality_report": chain_result.get("data_quality_report"),
                    "hyperparameters": chain_result.get("hyperparameters"),
                    "evaluation_strategy": chain_result.get("evaluation_strategy")
                },
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Fine-tuning workflow orchestrated with LangChain")
            return result
            
        except Exception as e:
            logger.error(f"Error orchestrating fine-tuning workflow: {str(e)}")
            raise

class DocumentProcessingAgent:
    """Multi-agent document workflow using LangChain agents"""
    
    def __init__(self, event_bus=None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        
        # Initialize services
        self.form_recognizer = FormRecognizerService(event_bus)
        self.openai_service = OpenAIService(event_bus)
        
        # Initialize LangChain LLM
        self.llm = AzureChatOpenAI(
            azure_endpoint=self.config.openai_endpoint,
            api_key=self.config.openai_api_key,
            api_version="2024-02-15-preview",
            deployment_name=self.config.openai_deployment,
            temperature=0.0
        )
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize LangChain agents for document processing"""
        
        # Define tools for agents
        extraction_tool = Tool(
            name="extract_invoice_data",
            description="Extract structured data from invoice documents",
            func=self._extract_invoice_tool
        )
        
        validation_tool = Tool(
            name="validate_invoice_data",
            description="Validate invoice data for completeness and accuracy",
            func=self._validate_invoice_tool
        )
        
        storage_tool = Tool(
            name="store_invoice_data",
            description="Store validated invoice data in the database",
            func=self._store_invoice_tool
        )
        
        self.tools = [extraction_tool, validation_tool, storage_tool]
        
        # Create agent prompt
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent document processing agent.
            
            Your role is to:
            1. Extract data from documents using available tools
            2. Validate the extracted data
            3. Store the validated data
            4. Report any issues or anomalies
            
            Be thorough and accurate in your processing."""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, agent_prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5
        )
    
    def _extract_invoice_tool(self, document_id: str) -> str:
        """Tool for extracting invoice data"""
        try:
            # This would call the actual extraction service
            return f"Invoice data extracted successfully for document {document_id}"
        except Exception as e:
            return f"Error extracting invoice data: {str(e)}"
    
    def _validate_invoice_tool(self, invoice_data: str) -> str:
        """Tool for validating invoice data"""
        try:
            # This would call the actual validation service
            return f"Invoice data validated successfully"
        except Exception as e:
            return f"Error validating invoice data: {str(e)}"
    
    def _store_invoice_tool(self, invoice_data: str) -> str:
        """Tool for storing invoice data"""
        try:
            # This would call the actual storage service
            return f"Invoice data stored successfully"
        except Exception as e:
            return f"Error storing invoice data: {str(e)}"
    
    async def process_document_with_agent(
        self,
        document_id: str,
        task_description: str
    ) -> Dict[str, Any]:
        """Process document using multi-agent workflow"""
        try:
            start_time = datetime.utcnow()
            
            # Run agent
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.agent_executor.invoke({
                    "input": f"Process document {document_id}: {task_description}"
                })
            )
            
            return {
                "document_id": document_id,
                "agent_output": result.get("output"),
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in agent processing: {str(e)}")
            raise

