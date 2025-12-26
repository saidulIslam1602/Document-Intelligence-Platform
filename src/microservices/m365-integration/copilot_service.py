"""
Microsoft 365 Copilot Integration Service
Advanced integration with M365 ecosystem for document intelligence
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import requests
from msal import ConfidentialClientApplication
from azure.identity import ClientSecretCredential
from azure.graph import GraphServiceClient
from azure.graph.models import User, DriveItem, Message, Chat
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
from transformers import AutoTokenizer, AutoModel
import torch

from src.shared.config.settings import config_manager
from src.shared.events.event_sourcing import DomainEvent, EventType, EventBus

class M365CopilotService:
    """Microsoft 365 Copilot integration service for document intelligence"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Microsoft Graph API client
        self.credential = ClientSecretCredential(
            tenant_id=self.config.tenant_id,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret
        )
        self.graph_client = GraphServiceClient(credential=self.credential)
        
        # OpenAI client for Copilot-like functionality
        self.openai_client = openai.AzureOpenAI(
            api_key=self.config.openai_api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=self.config.openai_endpoint
        )
        
        # M365 Services
        self.services = {
            'outlook': self._init_outlook_service(),
            'teams': self._init_teams_service(),
            'sharepoint': self._init_sharepoint_service(),
            'onedrive': self._init_onedrive_service(),
            'word': self._init_word_service(),
            'excel': self._init_excel_service(),
            'powerpoint': self._init_powerpoint_service()
        }
        
        # Document intelligence models
        self.document_models = {
            'classification': self._load_document_classifier(),
            'summarization': self._load_summarization_model(),
            'qa': self._load_qa_model(),
            'translation': self._load_translation_model()
        }
    
    async def process_m365_document(self, document_id: str, user_id: str, 
                                  service: str) -> Dict[str, Any]:
        """Process document from M365 service with Copilot-like intelligence"""
        try:
            # Get document from M365 service
            document = await self._get_document_from_m365(document_id, service, user_id)
            
            # Extract content based on service type
            content = await self._extract_content(document, service)
            
            # Apply Copilot-like intelligence
            intelligence_result = await self._apply_copilot_intelligence(content, service)
            
            # Generate insights and recommendations
            insights = await self._generate_insights(intelligence_result, service)
            
            # Create Copilot response
            copilot_response = await self._create_copilot_response(insights, service)
            
            return {
                'document_id': document_id,
                'service': service,
                'user_id': user_id,
                'content': content,
                'intelligence_result': intelligence_result,
                'insights': insights,
                'copilot_response': copilot_response,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing M365 document: {str(e)}")
            raise
    
    async def generate_copilot_suggestions(self, context: str, user_id: str, 
                                         service: str) -> List[Dict[str, Any]]:
        """Generate Copilot-like suggestions based on context"""
        try:
            # Get user's recent activity
            recent_activity = await self._get_user_recent_activity(user_id, service)
            
            # Analyze context and activity
            analysis = await self._analyze_context_and_activity(context, recent_activity)
            
            # Generate suggestions using AI
            suggestions = await self._generate_ai_suggestions(analysis, service)
            
            # Rank suggestions by relevance
            ranked_suggestions = await self._rank_suggestions(suggestions, context)
            
            return ranked_suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating Copilot suggestions: {str(e)}")
            raise
    
    async def analyze_team_collaboration(self, team_id: str) -> Dict[str, Any]:
        """Analyze team collaboration patterns using M365 data"""
        try:
            # Get team data from Microsoft Teams
            team_data = await self._get_team_data(team_id)
            
            # Analyze communication patterns
            communication_analysis = await self._analyze_communication_patterns(team_data)
            
            # Analyze document collaboration
            document_analysis = await self._analyze_document_collaboration(team_data)
            
            # Generate collaboration insights
            insights = await self._generate_collaboration_insights(
                communication_analysis, document_analysis
            )
            
            return {
                'team_id': team_id,
                'communication_analysis': communication_analysis,
                'document_analysis': document_analysis,
                'insights': insights,
                'recommendations': await self._generate_collaboration_recommendations(insights),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing team collaboration: {str(e)}")
            raise
    
    async def optimize_workflow_efficiency(self, user_id: str) -> Dict[str, Any]:
        """Optimize workflow efficiency using M365 data and AI"""
        try:
            # Get user's workflow data
            workflow_data = await self._get_user_workflow_data(user_id)
            
            # Analyze workflow patterns
            pattern_analysis = await self._analyze_workflow_patterns(workflow_data)
            
            # Identify bottlenecks and inefficiencies
            bottlenecks = await self._identify_bottlenecks(pattern_analysis)
            
            # Generate optimization recommendations
            recommendations = await self._generate_optimization_recommendations(
                pattern_analysis, bottlenecks
            )
            
            # Create automated workflow improvements
            improvements = await self._create_workflow_improvements(recommendations)
            
            return {
                'user_id': user_id,
                'pattern_analysis': pattern_analysis,
                'bottlenecks': bottlenecks,
                'recommendations': recommendations,
                'improvements': improvements,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing workflow efficiency: {str(e)}")
            raise
    
    async def _get_document_from_m365(self, document_id: str, service: str, 
                                    user_id: str) -> Dict[str, Any]:
        """Get document from M365 service"""
        try:
            if service == 'sharepoint':
                return await self._get_sharepoint_document(document_id, user_id)
            elif service == 'onedrive':
                return await self._get_onedrive_document(document_id, user_id)
            elif service == 'teams':
                return await self._get_teams_document(document_id, user_id)
            else:
                raise ValueError(f"Unsupported service: {service}")
                
        except Exception as e:
            self.logger.error(f"Error getting document from M365: {str(e)}")
            raise
    
    async def _get_sharepoint_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """Get document from SharePoint"""
        try:
            # Get SharePoint site
            sites = await self.graph_client.sites.get()
            
            # Find document in SharePoint
            for site in sites.value:
                try:
                    drive_items = await self.graph_client.sites[site.id].drive.items.get()
                    for item in drive_items.value:
                        if item.id == document_id:
                            return {
                                'id': item.id,
                                'name': item.name,
                                'content': await self._download_item_content(item),
                                'metadata': {
                                    'created_by': item.created_by,
                                    'modified_by': item.last_modified_by,
                                    'created_date': item.created_date_time,
                                    'modified_date': item.last_modified_date_time,
                                    'size': item.size,
                                    'web_url': item.web_url
                                }
                            }
                except Exception:
                    continue
            
            raise ValueError(f"Document {document_id} not found in SharePoint")
            
        except Exception as e:
            self.logger.error(f"Error getting SharePoint document: {str(e)}")
            raise
    
    async def _get_onedrive_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """Get document from OneDrive"""
        try:
            # Get user's OneDrive
            drive = await self.graph_client.users[user_id].drive.get()
            
            # Get document
            item = await self.graph_client.users[user_id].drive.items[document_id].get()
            
            return {
                'id': item.id,
                'name': item.name,
                'content': await self._download_item_content(item),
                'metadata': {
                    'created_by': item.created_by,
                    'modified_by': item.last_modified_by,
                    'created_date': item.created_date_time,
                    'modified_date': item.last_modified_date_time,
                    'size': item.size,
                    'web_url': item.web_url
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting OneDrive document: {str(e)}")
            raise
    
    async def _get_teams_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """Get document from Teams"""
        try:
            # Get Teams channels
            teams = await self.graph_client.me.joined_teams.get()
            
            for team in teams.value:
                try:
                    channels = await self.graph_client.teams[team.id].channels.get()
                    for channel in channels.value:
                        try:
                            messages = await self.graph_client.teams[team.id].channels[channel.id].messages.get()
                            for message in messages.value:
                                if message.id == document_id:
                                    return {
                                        'id': message.id,
                                        'name': f"Teams Message - {channel.display_name}",
                                        'content': message.body.content,
                                        'metadata': {
                                            'created_by': message.from_,
                                            'created_date': message.created_date_time,
                                            'channel': channel.display_name,
                                            'team': team.display_name
                                        }
                                    }
                        except Exception:
                            continue
                except Exception:
                    continue
            
            raise ValueError(f"Document {document_id} not found in Teams")
            
        except Exception as e:
            self.logger.error(f"Error getting Teams document: {str(e)}")
            raise
    
    async def _extract_content(self, document: Dict[str, Any], service: str) -> str:
        """Extract content from document based on service type"""
        try:
            if service in ['sharepoint', 'onedrive']:
                # Extract text from Office documents
                return await self._extract_office_document_content(document)
            elif service == 'teams':
                # Extract text from Teams messages
                return document['content']
            else:
                return document.get('content', '')
                
        except Exception as e:
            self.logger.error(f"Error extracting content: {str(e)}")
            raise
    
    async def _extract_office_document_content(self, document: Dict[str, Any]) -> str:
        """Extract content from Office documents"""
        try:
            # Use Azure Form Recognizer or similar service
            # This is a simplified version
            content = document.get('content', '')
            
            # If content is not directly available, download and process
            if not content:
                content = await self._download_and_process_document(document)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error extracting Office document content: {str(e)}")
            raise
    
    async def _apply_copilot_intelligence(self, content: str, service: str) -> Dict[str, Any]:
        """Apply Copilot-like intelligence to content"""
        try:
            # Document classification
            classification = await self._classify_document(content)
            
            # Key information extraction
            key_info = await self._extract_key_information(content)
            
            # Sentiment analysis
            sentiment = await self._analyze_sentiment(content)
            
            # Entity extraction
            entities = await self._extract_entities(content)
            
            # Generate summary
            summary = await self._generate_summary(content)
            
            # Generate questions and answers
            qa_pairs = await self._generate_qa_pairs(content)
            
            return {
                'classification': classification,
                'key_information': key_info,
                'sentiment': sentiment,
                'entities': entities,
                'summary': summary,
                'qa_pairs': qa_pairs,
                'confidence_scores': await self._calculate_confidence_scores(content)
            }
            
        except Exception as e:
            self.logger.error(f"Error applying Copilot intelligence: {str(e)}")
            raise
    
    async def _generate_insights(self, intelligence_result: Dict[str, Any], 
                               service: str) -> Dict[str, Any]:
        """Generate insights from intelligence result"""
        try:
            insights = {
                'document_type': intelligence_result['classification']['type'],
                'key_topics': await self._extract_key_topics(intelligence_result['entities']),
                'action_items': await self._extract_action_items(intelligence_result['key_information']),
                'collaboration_opportunities': await self._identify_collaboration_opportunities(
                    intelligence_result, service
                ),
                'follow_up_suggestions': await self._generate_follow_up_suggestions(
                    intelligence_result
                ),
                'productivity_tips': await self._generate_productivity_tips(
                    intelligence_result, service
                )
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")
            raise
    
    async def _create_copilot_response(self, insights: Dict[str, Any], 
                                     service: str) -> str:
        """Create Copilot-like response"""
        try:
            prompt = f"""
            Based on the following insights from a {service} document, create a helpful Copilot response:
            
            Document Type: {insights['document_type']}
            Key Topics: {', '.join(insights['key_topics'])}
            Action Items: {', '.join(insights['action_items'])}
            Collaboration Opportunities: {', '.join(insights['collaboration_opportunities'])}
            
            Create a concise, helpful response that:
            1. Summarizes the key points
            2. Suggests next steps
            3. Offers to help with related tasks
            4. Maintains a helpful, professional tone
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are Microsoft Copilot, a helpful AI assistant for Microsoft 365."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error creating Copilot response: {str(e)}")
            raise
    
    async def _get_user_recent_activity(self, user_id: str, service: str) -> List[Dict[str, Any]]:
        """Get user's recent activity from M365 service"""
        try:
            if service == 'outlook':
                return await self._get_outlook_activity(user_id)
            elif service == 'teams':
                return await self._get_teams_activity(user_id)
            elif service == 'sharepoint':
                return await self._get_sharepoint_activity(user_id)
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting user activity: {str(e)}")
            return []
    
    async def _get_outlook_activity(self, user_id: str) -> List[Dict[str, Any]]:
        """Get Outlook activity"""
        try:
            # Get recent emails
            messages = await self.graph_client.users[user_id].messages.get(
                orderby="receivedDateTime desc",
                top=10
            )
            
            activity = []
            for message in messages.value:
                activity.append({
                    'type': 'email',
                    'subject': message.subject,
                    'received_date': message.received_date_time,
                    'sender': message.from_,
                    'importance': message.importance
                })
            
            return activity
            
        except Exception as e:
            self.logger.error(f"Error getting Outlook activity: {str(e)}")
            return []
    
    async def _get_teams_activity(self, user_id: str) -> List[Dict[str, Any]]:
        """Get Teams activity"""
        try:
            # Get recent Teams messages
            teams = await self.graph_client.me.joined_teams.get()
            
            activity = []
            for team in teams.value:
                try:
                    channels = await self.graph_client.teams[team.id].channels.get()
                    for channel in channels.value:
                        try:
                            messages = await self.graph_client.teams[team.id].channels[channel.id].messages.get(
                                orderby="createdDateTime desc",
                                top=5
                            )
                            for message in messages.value:
                                activity.append({
                                    'type': 'teams_message',
                                    'content': message.body.content,
                                    'created_date': message.created_date_time,
                                    'channel': channel.display_name,
                                    'team': team.display_name
                                })
                        except Exception:
                            continue
                except Exception:
                    continue
            
            return activity
            
        except Exception as e:
            self.logger.error(f"Error getting Teams activity: {str(e)}")
            return []
    
    async def _get_sharepoint_activity(self, user_id: str) -> List[Dict[str, Any]]:
        """Get SharePoint activity"""
        try:
            # Get recent SharePoint files
            sites = await self.graph_client.sites.get()
            
            activity = []
            for site in sites.value:
                try:
                    drive_items = await self.graph_client.sites[site.id].drive.recent.get()
                    for item in drive_items.value:
                        activity.append({
                            'type': 'sharepoint_file',
                            'name': item.name,
                            'modified_date': item.last_modified_date_time,
                            'modified_by': item.last_modified_by,
                            'site': site.display_name
                        })
                except Exception:
                    continue
            
            return activity
            
        except Exception as e:
            self.logger.error(f"Error getting SharePoint activity: {str(e)}")
            return []
    
    async def _analyze_context_and_activity(self, context: str, 
                                          activity: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze context and user activity"""
        try:
            # Combine context and activity
            combined_text = context + " " + " ".join([
                item.get('subject', '') or item.get('content', '') or item.get('name', '')
                for item in activity
            ])
            
            # Extract key themes
            themes = await self._extract_themes(combined_text)
            
            # Identify patterns
            patterns = await self._identify_patterns(activity)
            
            # Calculate relevance scores
            relevance_scores = await self._calculate_relevance_scores(context, activity)
            
            return {
                'themes': themes,
                'patterns': patterns,
                'relevance_scores': relevance_scores,
                'activity_summary': await self._summarize_activity(activity)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing context and activity: {str(e)}")
            raise
    
    async def _generate_ai_suggestions(self, analysis: Dict[str, Any], 
                                     service: str) -> List[Dict[str, Any]]:
        """Generate AI-powered suggestions"""
        try:
            suggestions = []
            
            # Generate suggestions based on themes
            for theme in analysis['themes']:
                suggestions.append({
                    'type': 'theme_based',
                    'title': f"Explore {theme}",
                    'description': f"Continue working on {theme} related tasks",
                    'confidence': 0.8,
                    'action': f"Search for {theme} in {service}"
                })
            
            # Generate suggestions based on patterns
            for pattern in analysis['patterns']:
                suggestions.append({
                    'type': 'pattern_based',
                    'title': f"Follow {pattern} pattern",
                    'description': f"Continue the {pattern} workflow",
                    'confidence': 0.7,
                    'action': f"Apply {pattern} pattern"
                })
            
            # Generate suggestions based on relevance
            for item, score in analysis['relevance_scores'].items():
                if score > 0.6:
                    suggestions.append({
                        'type': 'relevance_based',
                        'title': f"Related to {item}",
                        'description': f"This is highly relevant to your recent activity",
                        'confidence': score,
                        'action': f"Review {item}"
                    })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating AI suggestions: {str(e)}")
            raise
    
    async def _rank_suggestions(self, suggestions: List[Dict[str, Any]], 
                              context: str) -> List[Dict[str, Any]]:
        """Rank suggestions by relevance"""
        try:
            # Calculate relevance scores
            for suggestion in suggestions:
                relevance_score = await self._calculate_suggestion_relevance(
                    suggestion, context
                )
                suggestion['relevance_score'] = relevance_score
            
            # Sort by relevance score
            suggestions.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            self.logger.error(f"Error ranking suggestions: {str(e)}")
            raise
    
    # Helper methods for service initialization
    def _init_outlook_service(self):
        """Initialize Outlook service"""
        return {
            'client': self.graph_client,
            'endpoint': 'users/{user_id}/messages'
        }
    
    def _init_teams_service(self):
        """Initialize Teams service"""
        return {
            'client': self.graph_client,
            'endpoint': 'teams/{team_id}/channels/{channel_id}/messages'
        }
    
    def _init_sharepoint_service(self):
        """Initialize SharePoint service"""
        return {
            'client': self.graph_client,
            'endpoint': 'sites/{site_id}/drive/items'
        }
    
    def _init_onedrive_service(self):
        """Initialize OneDrive service"""
        return {
            'client': self.graph_client,
            'endpoint': 'users/{user_id}/drive/items'
        }
    
    def _init_word_service(self):
        """Initialize Word service"""
        return {
            'client': self.graph_client,
            'endpoint': 'users/{user_id}/drive/items/{item_id}/workbook'
        }
    
    def _init_excel_service(self):
        """Initialize Excel service"""
        return {
            'client': self.graph_client,
            'endpoint': 'users/{user_id}/drive/items/{item_id}/workbook'
        }
    
    def _init_powerpoint_service(self):
        """Initialize PowerPoint service"""
        return {
            'client': self.graph_client,
            'endpoint': 'users/{user_id}/drive/items/{item_id}/workbook'
        }
    
    # Helper methods for model loading
    def _load_document_classifier(self):
        """Load document classification model"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            # Load a pre-trained document classification model
            model_name = "microsoft/DialoGPT-medium"  # Using a general model for document classification
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=10,  # Adjust based on your document types
                problem_type="single_label_classification"
            )
            
            # Set to evaluation mode
            model.eval()
            
            return {
                'tokenizer': tokenizer,
                'model': model,
                'device': torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            }
        except Exception as e:
            self.logger.error(f"Failed to load document classifier: {str(e)}")
            return None
    
    def _load_summarization_model(self):
        """Load summarization model"""
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            
            # Load a pre-trained summarization model
            model_name = "facebook/bart-large-cnn"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            return {
                'tokenizer': tokenizer,
                'model': model,
                'max_length': 1024,
                'min_length': 50
            }
        except Exception as e:
            self.logger.error(f"Failed to load summarization model: {str(e)}")
            return None
    
    def _load_qa_model(self):
        """Load Q&A model"""
        try:
            from transformers import AutoTokenizer, AutoModelForQuestionAnswering
            
            # Load a pre-trained Q&A model
            model_name = "distilbert-base-cased-distilled-squad"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForQuestionAnswering.from_pretrained(model_name)
            
            return {
                'tokenizer': tokenizer,
                'model': model,
                'max_length': 512
            }
        except Exception as e:
            self.logger.error(f"Failed to load Q&A model: {str(e)}")
            return None
    
    def _load_translation_model(self):
        """Load translation model"""
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            
            # Load a pre-trained translation model
            model_name = "Helsinki-NLP/opus-mt-en-de"  # English to German example
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            return {
                'tokenizer': tokenizer,
                'model': model,
                'max_length': 512
            }
        except Exception as e:
            self.logger.error(f"Failed to load translation model: {str(e)}")
            return None
    
    # Additional helper methods would be implemented here
    # for document processing, content extraction, etc.