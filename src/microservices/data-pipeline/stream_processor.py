"""
Advanced Stream Processing Pipeline
Real-time data processing using Azure Event Hubs and Stream Analytics
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.aio import EventHubConsumerClient
from azure.eventhub.extensions.checkpointstoreblobaio import BlobCheckpointStore
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.mgmt.streamanalytics import StreamAnalyticsManagementClient
from azure.mgmt.streamanalytics.models import StreamingJob, StreamingJobProperties, Sku
from azure.identity import DefaultAzureCredential

from src.shared.config.settings import config_manager
from src.shared.events.event_sourcing import DomainEvent, EventType, EventBus

class StreamProcessor:
    """Advanced stream processing for real-time document analytics"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Event Hub clients
        self.producer_client = EventHubProducerClient.from_connection_string(
            self.config.event_hub_connection_string,
            eventhub_name="document-processing"
        )
        
        # Checkpoint store for consumer
        self.checkpoint_store = BlobCheckpointStore.from_connection_string(
            self.config.storage_connection_string,
            container_name="checkpoints"
        )
        
        self.consumer_client = EventHubConsumerClient.from_connection_string(
            self.config.event_hub_connection_string,
            consumer_group="$Default",
            eventhub_name="document-processing",
            checkpoint_store=self.checkpoint_store
        )
        
        # Service Bus for reliable messaging
        self.service_bus_client = ServiceBusClient.from_connection_string(
            self.config.service_bus_connection_string
        )
        
        # SQL Database for storing processed data
        from src.shared.storage.sql_service import SQLService
        self.sql_service = SQLService(self.config.sql_connection_string)
        
        # Processing metrics
        self.metrics = {
            'events_processed': 0,
            'events_failed': 0,
            'processing_time_avg': 0.0,
            'last_processed': None,
            'throughput_per_minute': 0.0
        }
        
        # Processing windows
        self.processing_windows = {
            'tumbling_1min': 60,
            'tumbling_5min': 300,
            'sliding_1min': 60,
            'session_5min': 300
        }
    
    async def start_processing(self):
        """Start the stream processing pipeline"""
        try:
            self.logger.info("Starting stream processing pipeline")
            
            # Start consumer
            await self.consumer_client.receive(
                on_event=self._process_event,
                starting_position="-1",
                max_wait_time=5.0
            )
            
        except Exception as e:
            self.logger.error(f"Error starting stream processing: {str(e)}")
            raise
    
    async def stop_processing(self):
        """Stop the stream processing pipeline"""
        try:
            await self.consumer_client.close()
            await self.producer_client.close()
            await self.service_bus_client.close()
            self.logger.info("Stream processing pipeline stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping stream processing: {str(e)}")
            raise
    
    async def publish_event(self, event: DomainEvent, partition_key: str = None):
        """Publish event to Event Hub"""
        try:
            event_data = EventData(json.dumps(event.to_dict()))
            event_data.properties = {
                'event_type': event.event_type.value,
                'aggregate_id': event.aggregate_id,
                'timestamp': event.timestamp.isoformat()
            }
            
            async with self.producer_client:
                await self.producer_client.send_batch(
                    [event_data],
                    partition_key=partition_key or event.aggregate_id
                )
            
            self.logger.debug(f"Event {event.event_type.value} published for aggregate {event.aggregate_id}")
            
        except Exception as e:
            self.logger.error(f"Error publishing event: {str(e)}")
            raise
    
    async def _process_event(self, partition_context, event):
        """Process individual event from Event Hub"""
        try:
            start_time = datetime.utcnow()
            
            # Parse event data
            event_data = json.loads(event.body_as_str())
            event_type = event_data.get('event_type')
            
            # Route event to appropriate handler
            if event_type == EventType.DOCUMENT_UPLOADED.value:
                await self._handle_document_uploaded(event_data)
            elif event_type == EventType.DOCUMENT_PROCESSING_STARTED.value:
                await self._handle_processing_started(event_data)
            elif event_type == EventType.DOCUMENT_PROCESSING_COMPLETED.value:
                await self._handle_processing_completed(event_data)
            elif event_type == EventType.DOCUMENT_PROCESSING_FAILED.value:
                await self._handle_processing_failed(event_data)
            else:
                await self._handle_generic_event(event_data)
            
            # Update metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(processing_time)
            
            # Checkpoint event
            await partition_context.update_checkpoint(event)
            
        except Exception as e:
            self.logger.error(f"Error processing event: {str(e)}")
            self.metrics['events_failed'] += 1
            raise
    
    async def _handle_document_uploaded(self, event_data: Dict[str, Any]):
        """Handle document uploaded event"""
        try:
            document_id = event_data['aggregate_id']
            file_name = event_data['event_data']['file_name']
            file_size = event_data['event_data']['file_size']
            
            # Create processing record
            processing_record = {
                'id': f"processing_{document_id}",
                'document_id': document_id,
                'file_name': file_name,
                'file_size': file_size,
                'status': 'uploaded',
                'uploaded_at': datetime.utcnow().isoformat(),
                'partition_key': document_id
            }
            
            # Store in Azure SQL Database
            container = self.database.get_container_client('processing_records')
            await container.create_item(processing_record)
            
            # Publish to Service Bus for reliable processing
            async with self.service_bus_client:
                sender = self.service_bus_client.get_queue_sender(queue_name="document-processing")
                message = ServiceBusMessage(json.dumps(processing_record))
                await sender.send_messages(message)
            
            self.logger.info(f"Document {document_id} uploaded and queued for processing")
            
        except Exception as e:
            self.logger.error(f"Error handling document uploaded event: {str(e)}")
            raise
    
    async def _handle_processing_started(self, event_data: Dict[str, Any]):
        """Handle processing started event"""
        try:
            document_id = event_data['aggregate_id']
            processing_pipeline = event_data['event_data']['processing_pipeline']
            
            # Update processing record
            container = self.database.get_container_client('processing_records')
            processing_record = await container.read_item(
                item=f"processing_{document_id}",
                partition_key=document_id
            )
            
            processing_record['status'] = 'processing'
            processing_record['processing_pipeline'] = processing_pipeline
            processing_record['processing_started_at'] = datetime.utcnow().isoformat()
            
            await container.replace_item(
                item=f"processing_{document_id}",
                body=processing_record
            )
            
            self.logger.info(f"Processing started for document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling processing started event: {str(e)}")
            raise
    
    async def _handle_processing_completed(self, event_data: Dict[str, Any]):
        """Handle processing completed event"""
        try:
            document_id = event_data['aggregate_id']
            processing_result = event_data['event_data']['processing_result']
            processing_duration = event_data['event_data']['processing_duration']
            
            # Update processing record
            container = self.database.get_container_client('processing_records')
            processing_record = await container.read_item(
                item=f"processing_{document_id}",
                partition_key=document_id
            )
            
            processing_record['status'] = 'completed'
            processing_record['processing_result'] = processing_result
            processing_record['processing_duration'] = processing_duration
            processing_record['completed_at'] = datetime.utcnow().isoformat()
            
            await container.replace_item(
                item=f"processing_{document_id}",
                body=processing_record
            )
            
            # Store analytics data
            await self._store_analytics_data(document_id, processing_result)
            
            self.logger.info(f"Processing completed for document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling processing completed event: {str(e)}")
            raise
    
    async def _handle_processing_failed(self, event_data: Dict[str, Any]):
        """Handle processing failed event"""
        try:
            document_id = event_data['aggregate_id']
            error_message = event_data['event_data']['error_message']
            error_code = event_data['event_data']['error_code']
            retry_count = event_data['event_data']['retry_count']
            
            # Update processing record
            container = self.database.get_container_client('processing_records')
            processing_record = await container.read_item(
                item=f"processing_{document_id}",
                partition_key=document_id
            )
            
            processing_record['status'] = 'failed'
            processing_record['error_message'] = error_message
            processing_record['error_code'] = error_code
            processing_record['retry_count'] = retry_count
            processing_record['failed_at'] = datetime.utcnow().isoformat()
            
            await container.replace_item(
                item=f"processing_{document_id}",
                body=processing_record
            )
            
            # Handle retry logic
            if retry_count < 3:
                await self._schedule_retry(document_id, retry_count + 1)
            
            self.logger.error(f"Processing failed for document {document_id}: {error_message}")
            
        except Exception as e:
            self.logger.error(f"Error handling processing failed event: {str(e)}")
            raise
    
    async def _handle_generic_event(self, event_data: Dict[str, Any]):
        """Handle generic events"""
        try:
            # Store event for analytics
            container = self.database.get_container_client('events')
            event_record = {
                'id': event_data['event_id'],
                'event_type': event_data['event_type'],
                'aggregate_id': event_data['aggregate_id'],
                'event_data': event_data['event_data'],
                'timestamp': event_data['timestamp'],
                'partition_key': event_data['aggregate_id']
            }
            
            await container.create_item(event_record)
            
        except Exception as e:
            self.logger.error(f"Error handling generic event: {str(e)}")
            raise
    
    async def _store_analytics_data(self, document_id: str, processing_result: Dict[str, Any]):
        """Store analytics data for real-time dashboards"""
        try:
            analytics_data = {
                'id': f"analytics_{document_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'document_id': document_id,
                'document_type': processing_result.get('document_type', 'unknown'),
                'processing_duration': processing_result.get('processing_duration', 0),
                'confidence_score': processing_result.get('confidence', 0.0),
                'entities_count': len(processing_result.get('entities', {}).get('entities', {})),
                'sentiment': processing_result.get('sentiment', {}).get('sentiment', 'neutral'),
                'language': processing_result.get('language', 'unknown'),
                'timestamp': datetime.utcnow().isoformat(),
                'partition_key': document_id
            }
            
            container = self.database.get_container_client('analytics')
            await container.create_item(analytics_data)
            
        except Exception as e:
            self.logger.error(f"Error storing analytics data: {str(e)}")
            raise
    
    async def _schedule_retry(self, document_id: str, retry_count: int):
        """Schedule retry for failed processing"""
        try:
            retry_message = {
                'document_id': document_id,
                'retry_count': retry_count,
                'scheduled_at': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            
            async with self.service_bus_client:
                sender = self.service_bus_client.get_queue_sender(queue_name="retry-processing")
                message = ServiceBusMessage(json.dumps(retry_message))
                await sender.send_messages(message)
            
            self.logger.info(f"Retry scheduled for document {document_id}, attempt {retry_count}")
            
        except Exception as e:
            self.logger.error(f"Error scheduling retry: {str(e)}")
            raise
    
    def _update_metrics(self, processing_time: float):
        """Update processing metrics"""
        self.metrics['events_processed'] += 1
        self.metrics['last_processed'] = datetime.utcnow()
        
        # Update average processing time
        if self.metrics['processing_time_avg'] == 0:
            self.metrics['processing_time_avg'] = processing_time
        else:
            self.metrics['processing_time_avg'] = (
                self.metrics['processing_time_avg'] * 0.9 + processing_time * 0.1
            )
        
        # Calculate throughput per minute
        if self.metrics['last_processed']:
            time_diff = (datetime.utcnow() - self.metrics['last_processed']).total_seconds()
            if time_diff > 0:
                self.metrics['throughput_per_minute'] = (self.metrics['events_processed'] * 60) / time_diff
    
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics"""
        return {
            **self.metrics,
            'uptime': (datetime.utcnow() - self.metrics.get('start_time', datetime.utcnow())).total_seconds(),
            'success_rate': (
                (self.metrics['events_processed'] - self.metrics['events_failed']) / 
                max(self.metrics['events_processed'], 1)
            ) * 100
        }
    
    async def get_analytics_data(self, time_window: str = '1h') -> Dict[str, Any]:
        """Get analytics data for specified time window"""
        try:
            # Calculate time range
            now = datetime.utcnow()
            if time_window == '1h':
                start_time = now - timedelta(hours=1)
            elif time_window == '24h':
                start_time = now - timedelta(days=1)
            elif time_window == '7d':
                start_time = now - timedelta(days=7)
            else:
                start_time = now - timedelta(hours=1)
            
            # Query analytics data
            container = self.database.get_container_client('analytics')
            query = f"""
                SELECT 
                    c.document_type,
                    c.sentiment,
                    c.language,
                    AVG(c.processing_duration) as avg_processing_duration,
                    AVG(c.confidence_score) as avg_confidence,
                    COUNT(1) as document_count
                FROM c 
                WHERE c.timestamp >= '{start_time.isoformat()}'
                GROUP BY c.document_type, c.sentiment, c.language
            """
            
            results = list(container.query_items(query, enable_cross_partition_query=True))
            
            # Process results
            analytics = {
                'time_window': time_window,
                'total_documents': sum(r['document_count'] for r in results),
                'document_types': {},
                'sentiment_distribution': {},
                'language_distribution': {},
                'avg_processing_duration': 0.0,
                'avg_confidence': 0.0
            }
            
            total_duration = 0
            total_confidence = 0
            total_docs = 0
            
            for result in results:
                doc_type = result['document_type']
                sentiment = result['sentiment']
                language = result['language']
                count = result['document_count']
                duration = result['avg_processing_duration']
                confidence = result['avg_confidence']
                
                # Document types
                if doc_type not in analytics['document_types']:
                    analytics['document_types'][doc_type] = 0
                analytics['document_types'][doc_type] += count
                
                # Sentiment distribution
                if sentiment not in analytics['sentiment_distribution']:
                    analytics['sentiment_distribution'][sentiment] = 0
                analytics['sentiment_distribution'][sentiment] += count
                
                # Language distribution
                if language not in analytics['language_distribution']:
                    analytics['language_distribution'][language] = 0
                analytics['language_distribution'][language] += count
                
                total_duration += duration * count
                total_confidence += confidence * count
                total_docs += count
            
            if total_docs > 0:
                analytics['avg_processing_duration'] = total_duration / total_docs
                analytics['avg_confidence'] = total_confidence / total_docs
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting analytics data: {str(e)}")
            raise