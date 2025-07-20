import json
import pika
import asyncio
import time
from config import Config
from prometheus_client import Counter, Histogram
from metrics import metrics

# Enhanced metrics
rabbitmq_messages_published = Counter(
    'rabbitmq_messages_published_total',
    'Total messages published to RabbitMQ',
    ['queue', 'event_type']
)

rabbitmq_publish_duration = Histogram(
    'rabbitmq_publish_duration_seconds',
    'Time spent publishing to RabbitMQ',
    ['queue']
)

class AnalyticsClient:
    def __init__(self):
        self.rabbitmq_url = Config.RABBITMQ_URL
        self.connection = None
        self.channel = None
    
    async def _ensure_connection(self):
        """Ensure RabbitMQ connection is established"""
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = pika.BlockingConnection(
                    pika.URLParameters(self.rabbitmq_url)
                )
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue='analytics_events', durable=True)
            except Exception as e:
                print(f"Failed to connect to RabbitMQ: {e}")
                self.connection = None
                self.channel = None
    
    async def log_upscale_request(self, user_id: str, job_id: str, file_size: int, file_type: str):
        """Log upscale request via message queue"""
        event = {
            'event_type': 'upscale_request',
            'user_id': user_id,
            'job_id': job_id,
            'file_size': file_size,
            'file_type': file_type,
            'timestamp': time.time()
        }
        await self._publish_event(event)
    
    async def log_upscale_completion(self, job_id: str, processing_time: float, status: str):
        """Log upscale completion via message queue"""
        event = {
            'event_type': 'upscale_completion',
            'job_id': job_id,
            'processing_time_seconds': processing_time,
            'status': status,
            'timestamp': time.time()
        }
        await self._publish_event(event)
    
    async def _publish_event(self, event: dict):
        """Publish event to RabbitMQ with metrics"""
        start_time = time.time()
        try:
            await self._ensure_connection()
            if self.channel:
                self.channel.basic_publish(
                    exchange='',
                    routing_key='analytics_events',
                    body=json.dumps(event),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                rabbitmq_messages_published.labels(
                    queue='analytics_events',
                    event_type=event['event_type']
                ).inc()
                
                # Record in main metrics
                metrics.record_analytics_event(event['event_type'], "success")
            else:
                print(f"No RabbitMQ connection, logging locally: {json.dumps(event)}")
                metrics.record_analytics_event(event['event_type'], "failed")
        except Exception as e:
            print(f"Failed to publish analytics event: {e}")
            metrics.record_analytics_event(event.get('event_type', 'unknown'), "error")
        finally:
            duration = time.time() - start_time
            rabbitmq_publish_duration.labels(queue='analytics_events').observe(duration)

analytics_client = AnalyticsClient()
