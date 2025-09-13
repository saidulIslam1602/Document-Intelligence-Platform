"""
Event Sourcing Implementation
Implements event-driven architecture with event sourcing pattern for the Document Intelligence Platform
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Type, TypeVar
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import logging

# Type variables for generic event handling
T = TypeVar('T', bound='DomainEvent')
E = TypeVar('E', bound='AggregateRoot')

class EventType(Enum):
    """Event types enumeration"""
    # Document Events
    DOCUMENT_UPLOADED = "DocumentUploaded"
    DOCUMENT_PROCESSING_STARTED = "DocumentProcessingStarted"
    DOCUMENT_PROCESSING_COMPLETED = "DocumentProcessingCompleted"
    DOCUMENT_PROCESSING_FAILED = "DocumentProcessingFailed"
    DOCUMENT_CLASSIFIED = "DocumentClassified"
    DOCUMENT_ANALYZED = "DocumentAnalyzed"
    
    # AI Processing Events
    AI_PROCESSING_STARTED = "AIProcessingStarted"
    AI_PROCESSING_COMPLETED = "AIProcessingCompleted"
    AI_MODEL_TRAINED = "AIModelTrained"
    AI_MODEL_DEPLOYED = "AIModelDeployed"
    
    # Analytics Events
    ANALYTICS_CALCULATED = "AnalyticsCalculated"
    METRICS_UPDATED = "MetricsUpdated"
    ALERT_TRIGGERED = "AlertTriggered"
    
    # System Events
    SYSTEM_STARTED = "SystemStarted"
    SYSTEM_STOPPED = "SystemStopped"
    HEALTH_CHECK_FAILED = "HealthCheckFailed"

@dataclass
class DomainEvent(ABC):
    """Base class for all domain events"""
    event_id: str
    event_type: EventType
    aggregate_id: str
    aggregate_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    version: int
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_data": self.event_data,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create event from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            event_data=data["event_data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data["version"],
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            metadata=data.get("metadata", {})
        )

# Specific Event Implementations
@dataclass
class DocumentUploadedEvent(DomainEvent):
    """Event raised when a document is uploaded"""
    def __init__(self, document_id: str, file_name: str, file_size: int, 
                 content_type: str, user_id: str, correlation_id: str = None):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=EventType.DOCUMENT_UPLOADED,
            aggregate_id=document_id,
            aggregate_type="Document",
            event_data={
                "file_name": file_name,
                "file_size": file_size,
                "content_type": content_type,
                "user_id": user_id
            },
            timestamp=datetime.now(timezone.utc),
            version=1,
            correlation_id=correlation_id
        )

@dataclass
class DocumentProcessingStartedEvent(DomainEvent):
    """Event raised when document processing starts"""
    def __init__(self, document_id: str, processing_pipeline: str, 
                 estimated_duration: int, correlation_id: str = None):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=EventType.DOCUMENT_PROCESSING_STARTED,
            aggregate_id=document_id,
            aggregate_type="Document",
            event_data={
                "processing_pipeline": processing_pipeline,
                "estimated_duration": estimated_duration
            },
            timestamp=datetime.now(timezone.utc),
            version=2,
            correlation_id=correlation_id
        )

@dataclass
class DocumentProcessingCompletedEvent(DomainEvent):
    """Event raised when document processing completes successfully"""
    def __init__(self, document_id: str, processing_result: Dict[str, Any], 
                 processing_duration: int, correlation_id: str = None):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=EventType.DOCUMENT_PROCESSING_COMPLETED,
            aggregate_id=document_id,
            aggregate_type="Document",
            event_data={
                "processing_result": processing_result,
                "processing_duration": processing_duration
            },
            timestamp=datetime.now(timezone.utc),
            version=3,
            correlation_id=correlation_id
        )

@dataclass
class DocumentProcessingFailedEvent(DomainEvent):
    """Event raised when document processing fails"""
    def __init__(self, document_id: str, error_message: str, error_code: str,
                 retry_count: int, correlation_id: str = None):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=EventType.DOCUMENT_PROCESSING_FAILED,
            aggregate_id=document_id,
            aggregate_type="Document",
            event_data={
                "error_message": error_message,
                "error_code": error_code,
                "retry_count": retry_count
            },
            timestamp=datetime.now(timezone.utc),
            version=3,
            correlation_id=correlation_id
        )

@dataclass
class DocumentClassifiedEvent(DomainEvent):
    """Event raised when document is classified"""
    def __init__(self, document_id: str, document_type: str, confidence: float,
                 classification_model: str, correlation_id: str = None):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=EventType.DOCUMENT_CLASSIFIED,
            aggregate_id=document_id,
            aggregate_type="Document",
            event_data={
                "document_type": document_type,
                "confidence": confidence,
                "classification_model": classification_model
            },
            timestamp=datetime.now(timezone.utc),
            version=4,
            correlation_id=correlation_id
        )

class AggregateRoot(ABC):
    """Base class for aggregate roots in event sourcing"""
    
    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self.version = 0
        self.uncommitted_events: List[DomainEvent] = []
        self._correlation_id: Optional[str] = None
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get uncommitted events"""
        return self.uncommitted_events.copy()
    
    def mark_events_as_committed(self):
        """Mark all events as committed"""
        self.uncommitted_events.clear()
    
    def apply_event(self, event: DomainEvent):
        """Apply event to aggregate"""
        self._handle_event(event)
        self.version = event.version
        self.uncommitted_events.append(event)
    
    @abstractmethod
    def _handle_event(self, event: DomainEvent):
        """Handle specific event type"""
        pass
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for events"""
        self._correlation_id = correlation_id

class EventStore(ABC):
    """Abstract event store interface"""
    
    @abstractmethod
    async def append_events(self, events: List[DomainEvent]) -> None:
        """Append events to the event store"""
        pass
    
    @abstractmethod
    async def get_events(self, aggregate_id: str, from_version: int = 0) -> List[DomainEvent]:
        """Get events for an aggregate"""
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: EventType, 
                                from_timestamp: datetime = None) -> List[DomainEvent]:
        """Get events by type"""
        pass

class SQLEventStore(EventStore):
    """Azure SQL Database implementation of event store"""
    
    def __init__(self, sql_service):
        self.sql_service = sql_service
        self.logger = logging.getLogger(__name__)
    
    async def append_events(self, events: List[DomainEvent]) -> None:
        """Append events to Azure SQL Database"""
        try:
            for event in events:
                query = """
                INSERT INTO domain_events 
                (event_id, aggregate_id, event_type, event_data, timestamp, version)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                
                params = (
                    event.event_id,
                    event.aggregate_id,
                    event.event_type.value,
                    json.dumps(event.event_data),
                    event.timestamp,
                    1  # Version will be calculated properly in production
                )
                
                await self.sql_service.execute_non_query(query, params)
                self.logger.info(f"Event {event.event_type.value} stored for aggregate {event.aggregate_id}")
        except Exception as e:
            self.logger.error(f"Failed to append events: {str(e)}")
            raise
    
    async def get_events(self, aggregate_id: str, from_version: int = 0) -> List[DomainEvent]:
        """Get events for an aggregate from Azure SQL Database"""
        try:
            query = """
            SELECT event_id, aggregate_id, event_type, event_data, timestamp, version
            FROM domain_events 
            WHERE aggregate_id = ? AND version >= ?
            ORDER BY version
            """
            
            result = await self.sql_service.execute_query(query, (aggregate_id, from_version))
            
            events = []
            for row in result:
                event = DomainEvent(
                    event_type=EventType(row["event_type"]),
                    aggregate_id=row["aggregate_id"],
                    event_data=json.loads(row["event_data"]),
                    event_id=row["event_id"],
                    timestamp=row["timestamp"]
                )
                events.append(event)
            
            return events
        except Exception as e:
            self.logger.error(f"Failed to get events for aggregate {aggregate_id}: {str(e)}")
            raise
    
    async def get_events_by_type(self, event_type: EventType, 
                                from_timestamp: datetime = None) -> List[DomainEvent]:
        """Get events by type from Azure SQL Database"""
        try:
            if from_timestamp:
                query = """
                SELECT event_id, aggregate_id, event_type, event_data, timestamp, version
                FROM domain_events 
                WHERE event_type = ? AND timestamp >= ?
                ORDER BY timestamp
                """
                params = (event_type.value, from_timestamp)
            else:
                query = """
                SELECT event_id, aggregate_id, event_type, event_data, timestamp, version
                FROM domain_events 
                WHERE event_type = ?
                ORDER BY timestamp
                """
                params = (event_type.value,)
            
            result = await self.sql_service.execute_query(query, params)
            
            events = []
            for row in result:
                event = DomainEvent(
                    event_type=EventType(row["event_type"]),
                    aggregate_id=row["aggregate_id"],
                    event_data=json.loads(row["event_data"]),
                    event_id=row["event_id"],
                    timestamp=row["timestamp"]
                )
                events.append(event)
            
            return events
        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type.value}: {str(e)}")
            raise

class EventHandler(ABC):
    """Abstract event handler interface"""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event"""
        pass

class EventBus:
    """Event bus for publishing and subscribing to events"""
    
    def __init__(self):
        self.handlers: Dict[EventType, List[EventHandler]] = {}
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe to an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        self.logger.info(f"Handler {handler.__class__.__name__} subscribed to {event_type.value}")
    
    async def publish(self, event: DomainEvent):
        """Publish an event to all subscribers"""
        if event.event_type in self.handlers:
            tasks = []
            for handler in self.handlers[event.event_type]:
                task = asyncio.create_task(self._handle_event_safely(handler, event))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _handle_event_safely(self, handler: EventHandler, event: DomainEvent):
        """Handle event safely with error handling"""
        try:
            await handler.handle(event)
        except Exception as e:
            self.logger.error(f"Error handling event {event.event_type.value} with handler {handler.__class__.__name__}: {str(e)}")

# Event Handlers Implementation
class DocumentProcessingEventHandler(EventHandler):
    """Handles document processing events"""
    
    def __init__(self, event_store: EventStore, event_bus: EventBus):
        self.event_store = event_store
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle document processing events"""
        if event.event_type == EventType.DOCUMENT_UPLOADED:
            await self._handle_document_uploaded(event)
        elif event.event_type == EventType.DOCUMENT_PROCESSING_COMPLETED:
            await self._handle_processing_completed(event)
        elif event.event_type == EventType.DOCUMENT_PROCESSING_FAILED:
            await self._handle_processing_failed(event)
    
    async def _handle_document_uploaded(self, event: DocumentUploadedEvent):
        """Handle document uploaded event"""
        self.logger.info(f"Document {event.aggregate_id} uploaded, starting processing")
        
        # Start processing pipeline
        processing_started = DocumentProcessingStartedEvent(
            document_id=event.aggregate_id,
            processing_pipeline="ai-powered-pipeline",
            estimated_duration=30,
            correlation_id=event.correlation_id
        )
        
        await self.event_store.append_events([processing_started])
        await self.event_bus.publish(processing_started)
    
    async def _handle_processing_completed(self, event: DocumentProcessingCompletedEvent):
        """Handle processing completed event"""
        self.logger.info(f"Document {event.aggregate_id} processing completed")
        
        # Update analytics, send notifications, etc.
        # This would trigger other business processes
    
    async def _handle_processing_failed(self, event: DocumentProcessingFailedEvent):
        """Handle processing failed event"""
        self.logger.error(f"Document {event.aggregate_id} processing failed: {event.event_data['error_message']}")
        
        # Handle retry logic, alerting, etc.