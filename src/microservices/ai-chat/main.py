"""
AI Chat Microservice
Intelligent document Q&A and conversational AI interface
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import json
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

from ...shared.config.settings import config_manager
from ...shared.storage.sql_service import SQLService
from ...shared.auth.auth_service import get_current_user_id, User
from ...shared.utils.error_handler import handle_validation_error, ErrorHandler
from ...shared.cache.redis_cache import cache_service, cache_result, cache_invalidate, CacheKeys
# Import AI processing services
from ..ai_processing.openai_service import OpenAIService
from ..ai_processing.form_recognizer_service import FormRecognizerService

# Initialize FastAPI app
app = FastAPI(
    title="AI Chat Service",
    description="Intelligent document Q&A and conversational AI interface",
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

# Security
security = HTTPBearer()

# Global variables
config = config_manager.get_azure_config()
logger = logging.getLogger(__name__)

# Azure clients
sql_service = SQLService(config.sql_connection_string)
blob_service_client = BlobServiceClient.from_connection_string(
    config.storage_connection_string
)

# AI Services
openai_service = OpenAIService()
form_recognizer_service = FormRecognizerService()

# Cognitive Search client
search_client = SearchClient(
    endpoint=config.cognitive_search_endpoint,
    index_name="documents",
    credential=AzureKeyCredential(config.cognitive_search_key)
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, ConnectionClosedError, RuntimeError) as e:
                # Remove broken connections
                self.active_connections.remove(connection)
                self.logger.warning(f"Removed broken WebSocket connection: {str(e)}")
            except Exception as e:
                # Log unexpected errors but don't remove connection
                self.logger.error(f"Unexpected error sending message: {str(e)}")

manager = ConnectionManager()

# Pydantic models
class ChatMessage(BaseModel):
    message: str = Field(..., description="User's chat message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    document_id: Optional[str] = Field(None, description="Specific document to query")
    include_sources: bool = Field(True, description="Include source documents in response")

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[Dict[str, Any]] = []
    confidence: float
    timestamp: str

class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    title: str
    created_at: str
    last_message_at: str
    message_count: int

class DocumentContext(BaseModel):
    document_id: str
    title: str
    content: str
    relevance_score: float
    source_type: str

# Chat endpoints
@app.post("/chat/message", response_model=ChatResponse)
@handle_validation_error("chat message")
async def send_chat_message(
    chat_message: ChatMessage,
    user_id: str = Depends(get_current_user_id)
):
    """Send a chat message and get AI response"""
    try:
        # Generate or get conversation ID
        conversation_id = chat_message.conversation_id or f"conv_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Search for relevant documents
        relevant_docs = await search_relevant_documents(
            query=chat_message.message,
            user_id=user_id,
            document_id=chat_message.document_id
        )
        
        # Get conversation history
        conversation_history = await get_conversation_history(conversation_id)
        
        # Generate AI response
        ai_response = await generate_chat_response(
            message=chat_message.message,
            relevant_docs=relevant_docs,
            conversation_history=conversation_history,
            user_id=user_id
        )
        
        # Save conversation
        await save_conversation_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message=chat_message.message,
            response=ai_response["response"],
            sources=relevant_docs
        )
        
        # Prepare response
        response = ChatResponse(
            response=ai_response["response"],
            conversation_id=conversation_id,
            sources=relevant_docs if chat_message.include_sources else [],
            confidence=ai_response["confidence"],
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Chat response generated for user {user_id}")
        return response
        
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "chat message", 500, "Failed to process chat message"
        )

@app.get("/chat/conversations", response_model=List[Conversation])
@handle_validation_error("get conversations")
@cache_result(ttl=600, key_prefix="user_conversations")  # Cache for 10 minutes
async def get_user_conversations(
    user_id: str = Depends(get_current_user_id),
    limit: int = 20
):
    """Get user's chat conversations"""
    try:
        conversations = sql_service.get_user_conversations(user_id, limit)
        return [Conversation(**conv) for conv in conversations]
        
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "get conversations", 500, "Failed to get conversations"
        )

@app.get("/chat/conversations/{conversation_id}/messages")
@handle_validation_error("get conversation messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    limit: int = 50
):
    """Get messages from a specific conversation"""
    try:
        messages = sql_service.get_conversation_messages(conversation_id, user_id, limit)
        return {"messages": messages}
        
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "get conversation messages", 500, "Failed to get conversation messages"
        )

@app.delete("/chat/conversations/{conversation_id}")
@handle_validation_error("delete conversation")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a conversation and its messages"""
    try:
        # Delete conversation
        container = database.get_container_client("conversations")
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container.delete_item(
                item=conversation_id,
                partition_key=user_id
            )
        )
        
        # Delete messages
        messages_container = database.get_container_client("conversation_messages")
        query = f"""
        SELECT c.id FROM c 
        WHERE c.conversation_id = @conversation_id 
        AND c.user_id = @user_id
        """
        
        parameters = [
            {"name": "@conversation_id", "value": conversation_id},
            {"name": "@user_id", "value": user_id}
        ]
        
        for item in messages_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ):
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: messages_container.delete_item(
                    item=item["id"],
                    partition_key=user_id
                )
            )
        
        logger.info(f"Conversation {conversation_id} deleted for user {user_id}")
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        ErrorHandler.log_and_raise(
            logger, e, "delete conversation", 500, "Failed to delete conversation"
        )

# WebSocket endpoint for real-time chat
@app.websocket("/chat/ws")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process chat message
            chat_message = ChatMessage(**message_data)
            
            # Get AI response
            response = await send_chat_message(chat_message, user_id)
            
            # Send response back
            await manager.send_personal_message(
                json.dumps(response.dict()),
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

# Helper functions
async def search_relevant_documents(
    query: str, 
    user_id: str, 
    document_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for documents relevant to the chat query"""
    try:
        if document_id:
            # Search within specific document
            search_results = search_client.search(
                search_text=query,
                filter=f"document_id eq '{document_id}' and user_id eq '{user_id}'",
                top=5
            )
        else:
            # Search across user's documents
            search_results = search_client.search(
                search_text=query,
                filter=f"user_id eq '{user_id}'",
                top=10
            )
        
        relevant_docs = []
        for result in search_results:
            relevant_docs.append({
                "document_id": result["document_id"],
                "title": result.get("file_name", "Unknown"),
                "content": result.get("extracted_text", "")[:500] + "...",
                "relevance_score": result.get("@search.score", 0.0),
                "source_type": "document"
            })
        
        return relevant_docs
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return []

async def get_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    """Get conversation history for context"""
    try:
        container = database.get_container_client("conversation_messages")
        
        query = f"""
        SELECT c.message, c.response 
        FROM c 
        WHERE c.conversation_id = @conversation_id 
        ORDER BY c.timestamp DESC
        """
        
        parameters = [{"name": "@conversation_id", "value": conversation_id}]
        
        history = []
        for item in container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ):
            history.append({
                "user": item["message"],
                "assistant": item["response"]
            })
        
        return history[-10:]  # Last 10 exchanges
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return []

async def generate_chat_response(
    message: str,
    relevant_docs: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    user_id: str
) -> Dict[str, Any]:
    """Generate AI response using OpenAI"""
    try:
        # Build context from relevant documents
        context = ""
        for doc in relevant_docs[:3]:  # Use top 3 most relevant
            context += f"Document: {doc['title']}\nContent: {doc['content']}\n\n"
        
        # Build conversation context
        conversation_context = ""
        for exchange in conversation_history[-3:]:  # Last 3 exchanges
            conversation_context += f"User: {exchange['user']}\nAssistant: {exchange['assistant']}\n\n"
        
        # Create prompt for OpenAI
        prompt = f"""
You are an intelligent document assistant. You help users understand and analyze their documents.

Context from relevant documents:
{context}

Recent conversation:
{conversation_context}

User's current question: {message}

Please provide a helpful, accurate response based on the document context. If the information isn't available in the documents, say so clearly. Be concise but informative.

Response:
"""
        
        # Get response from OpenAI
        response = await openai_service.generate_completion(
            prompt=prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        # Calculate confidence based on document relevance
        confidence = 0.8
        if relevant_docs:
            avg_relevance = sum(doc["relevance_score"] for doc in relevant_docs) / len(relevant_docs)
            confidence = min(0.95, avg_relevance / 100)
        
        return {
            "response": response,
            "confidence": confidence
        }
        
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        return {
            "response": "I apologize, but I'm having trouble processing your request right now. Please try again later.",
            "confidence": 0.0
        }

async def save_conversation_message(
    conversation_id: str,
    user_id: str,
    message: str,
    response: str,
    sources: List[Dict[str, Any]]
):
    """Save conversation message to database"""
    try:
        # Save message
        message_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "message": message,
            "response": response,
            "sources": json.dumps(sources)
        }
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sql_service.store_conversation_message(message_data)
        )
        
        # Check if conversation exists, if not create it
        try:
            conversations = sql_service.get_user_conversations(user_id, 1)
            conversation_exists = any(conv['conversation_id'] == conversation_id for conv in conversations)
            
            if not conversation_exists:
                # Create new conversation
                conversation_data = {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "title": message[:50] + "..." if len(message) > 50 else message,
                    "last_message_at": datetime.utcnow().isoformat(),
                    "message_count": 1
                }
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: sql_service.store_conversation(conversation_data)
                )
        except Exception as e:
            logger.error(f"Error saving conversation message: {str(e)}")
    except Exception as e:
        logger.error(f"Error in save_conversation_message: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-chat",
        "timestamp": datetime.utcnow().isoformat()
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("AI Chat Service started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("AI Chat Service stopped")