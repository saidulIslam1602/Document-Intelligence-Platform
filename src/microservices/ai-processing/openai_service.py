"""
Azure OpenAI Service Integration
Advanced AI processing using Azure OpenAI for document intelligence
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import numpy as np
from azure.openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import DomainEvent, EventType, EventBus

class OpenAIService:
    """Azure OpenAI service for advanced document processing"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=self.config.openai_api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=self.config.openai_endpoint
        )
        
        # Initialize Cognitive Search client
        self.search_client = SearchClient(
            endpoint=self.config.cognitive_search_endpoint,
            index_name="documents",
            credential=AzureKeyCredential(self.config.cognitive_search_key)
        )
        
        # Model configurations
        self.models = {
            "gpt4": "gpt-4",
            "gpt35": "gpt-35-turbo",
            "embedding": "text-embedding-ada-002",
            "davinci": "text-davinci-003"
        }
    
    async def generate_summary(self, text: str, max_length: int = 200) -> Dict[str, Any]:
        """Generate document summary using GPT-4"""
        try:
            prompt = f"""
            Please provide a comprehensive summary of the following document text.
            Focus on key information, main topics, and important details.
            Keep the summary under {max_length} words.
            
            Document text:
            {text[:4000]}  # Limit input to avoid token limits
            """
            
            response = await self._call_openai(
                model=self.models["gpt4"],
                messages=[
                    {"role": "system", "content": "You are an expert document analyst. Provide clear, concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            return {
                "summary": summary,
                "word_count": len(summary.split()),
                "model_used": self.models["gpt4"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            raise
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities from text using GPT-4"""
        try:
            prompt = f"""
            Extract the following types of entities from the text:
            - PERSON: People mentioned
            - ORGANIZATION: Companies, institutions, organizations
            - LOCATION: Places, addresses, geographic locations
            - DATE: Dates and time references
            - MONEY: Monetary amounts and currencies
            - EMAIL: Email addresses
            - PHONE: Phone numbers
            - URL: Web addresses
            
            Return the results in JSON format with entity type as key and list of entities as value.
            
            Text:
            {text[:3000]}
            """
            
            response = await self._call_openai(
                model=self.models["gpt4"],
                messages=[
                    {"role": "system", "content": "You are an expert named entity recognition system. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            entities_json = response.choices[0].message.content
            entities = json.loads(entities_json)
            
            return {
                "entities": entities,
                "entity_count": sum(len(v) for v in entities.values()),
                "model_used": self.models["gpt4"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {str(e)}")
            raise
    
    async def answer_question(self, question: str, context: str = None, 
                            document_id: str = None) -> Dict[str, Any]:
        """Answer questions about documents using RAG (Retrieval-Augmented Generation)"""
        try:
            # If no context provided, search for relevant documents
            if not context and document_id:
                context = await self._search_relevant_content(question, document_id)
            
            prompt = f"""
            Based on the following context, answer the question accurately and concisely.
            If the answer cannot be found in the context, say "I cannot find the answer in the provided context."
            
            Context:
            {context or "No context provided"}
            
            Question: {question}
            
            Answer:
            """
            
            response = await self._call_openai(
                model=self.models["gpt4"],
                messages=[
                    {"role": "system", "content": "You are an expert document Q&A assistant. Provide accurate, helpful answers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.2
            )
            
            answer = response.choices[0].message.content
            
            return {
                "question": question,
                "answer": answer,
                "context_used": bool(context),
                "model_used": self.models["gpt4"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error answering question: {str(e)}")
            raise
    
    async def classify_document(self, text: str) -> Dict[str, Any]:
        """Classify document type using GPT-4"""
        try:
            prompt = f"""
            Classify this document into one of the following categories:
            - INVOICE: Bills, invoices, receipts, financial documents
            - CONTRACT: Legal agreements, contracts, terms of service
            - REPORT: Analytical reports, research papers, data analysis
            - CORRESPONDENCE: Emails, letters, memos, communications
            - TECHNICAL: Technical documentation, manuals, specifications
            - LEGAL: Legal documents, court papers, legal notices
            - MEDICAL: Medical records, prescriptions, health documents
            - OTHER: Any other document type
            
            Also provide a confidence score (0-1) and reasoning for the classification.
            
            Document text (first 2000 characters):
            {text[:2000]}
            
            Return in JSON format:
            {{
                "category": "CATEGORY_NAME",
                "confidence": 0.95,
                "reasoning": "Brief explanation of why this classification was chosen"
            }}
            """
            
            response = await self._call_openai(
                model=self.models["gpt4"],
                messages=[
                    {"role": "system", "content": "You are an expert document classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            classification_json = response.choices[0].message.content
            classification = json.loads(classification_json)
            
            return {
                "document_type": classification["category"],
                "confidence": classification["confidence"],
                "reasoning": classification["reasoning"],
                "model_used": self.models["gpt4"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error classifying document: {str(e)}")
            raise
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of document content"""
        try:
            prompt = f"""
            Analyze the sentiment of this text and provide:
            1. Overall sentiment (positive, negative, neutral)
            2. Sentiment score (-1 to 1, where -1 is very negative, 1 is very positive)
            3. Key emotional indicators
            4. Confidence level (0-1)
            
            Text:
            {text[:2000]}
            
            Return in JSON format:
            {{
                "sentiment": "positive/negative/neutral",
                "score": 0.8,
                "indicators": ["confident", "optimistic"],
                "confidence": 0.9
            }}
            """
            
            response = await self._call_openai(
                model=self.models["gpt4"],
                messages=[
                    {"role": "system", "content": "You are an expert sentiment analysis system. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            sentiment_json = response.choices[0].message.content
            sentiment = json.loads(sentiment_json)
            
            return {
                "sentiment": sentiment["sentiment"],
                "score": sentiment["score"],
                "indicators": sentiment["indicators"],
                "confidence": sentiment["confidence"],
                "model_used": self.models["gpt4"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            raise
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text using Azure OpenAI"""
        try:
            response = await self._call_openai(
                model=self.models["embedding"],
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search using vector embeddings"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embeddings(query)
            
            # Perform vector search
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )
            
            results = self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                select=["id", "title", "content", "metadata"],
                top=top_k
            )
            
            search_results = []
            for result in results:
                search_results.append({
                    "id": result["id"],
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("@search.score", 0)
                })
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Error performing semantic search: {str(e)}")
            raise
    
    async def _search_relevant_content(self, question: str, document_id: str) -> str:
        """Search for relevant content using semantic search"""
        try:
            # Perform semantic search
            search_results = await self.semantic_search(question, top_k=3)
            
            # Combine relevant content
            relevant_content = []
            for result in search_results:
                if result["id"] == document_id or "content" in result:
                    relevant_content.append(result["content"])
            
            return "\n\n".join(relevant_content)
            
        except Exception as e:
            self.logger.error(f"Error searching relevant content: {str(e)}")
            return ""
    
    async def _call_openai(self, model: str, **kwargs) -> Any:
        """Make async call to Azure OpenAI"""
        try:
            # Run the OpenAI call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.chat.completions.create(
                    model=model,
                    **kwargs
                )
            )
            return response
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {str(e)}")
            raise
    
    async def process_document_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple documents in batch"""
        try:
            results = []
            
            # Process documents concurrently
            tasks = []
            for doc in documents:
                task = self._process_single_document(doc)
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing document {i}: {str(result)}")
                    processed_results.append({
                        "document_id": documents[i].get("id", "unknown"),
                        "error": str(result),
                        "status": "failed"
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Error processing document batch: {str(e)}")
            raise
    
    async def _process_single_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document"""
        try:
            document_id = document.get("id")
            text = document.get("content", "")
            
            # Process document with multiple AI services
            tasks = [
                self.generate_summary(text),
                self.extract_entities(text),
                self.classify_document(text),
                self.analyze_sentiment(text)
            ]
            
            summary, entities, classification, sentiment = await asyncio.gather(*tasks)
            
            return {
                "document_id": document_id,
                "summary": summary,
                "entities": entities,
                "classification": classification,
                "sentiment": sentiment,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing single document: {str(e)}")
            raise