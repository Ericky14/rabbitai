from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter
from datetime import datetime
import os
import pika
import json

app = FastAPI(title="Analytics Service")

# Metrics
events_processed_total = Counter(
    'analytics_events_processed_total',
    'Total analytics events processed',
    ['event_type', 'status']
)

class AnalyticsService:
    def __init__(self):
        self.connection = None
        self.channel = None
    
    def setup_rabbitmq(self):
        """Setup RabbitMQ consumer for analytics events"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connection = pika.BlockingConnection(
                    pika.URLParameters(os.getenv('RABBITMQ_URL'))
                )
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue='analytics_events')
                self.channel.basic_consume(
                    queue='analytics_events',
                    on_message_callback=self.process_analytics_event,
                    auto_ack=True
                )
                print("Connected to RabbitMQ successfully")
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
    
    def start_consuming(self):
        """Start consuming messages from RabbitMQ"""
        try:
            self.setup_rabbitmq()
            if self.channel:
                print("Starting to consume analytics events...")
                self.channel.start_consuming()
        except Exception as e:
            print(f"Error consuming messages: {e}")
    
    def process_analytics_event(self, ch, method, properties, body):
        """Process analytics events from queue"""
        try:
            event = json.loads(body)
            events_processed_total.labels(event_type=event['event_type'], status='success').inc()
            print(f"Processed analytics event: {event['event_type']}")
        except Exception as e:
            events_processed_total.labels(event_type='unknown', status='error').inc()
            print(f"Failed to process analytics event: {e}")

analytics_service = AnalyticsService()

# Start consuming in a background thread
import threading
def start_consumer():
    analytics_service.start_consuming()

consumer_thread = threading.Thread(target=start_consumer, daemon=True)
consumer_thread.start()

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/events")
async def log_event(event: dict):
    """Direct API endpoint for logging events"""
    try:
        events_processed_total.labels(event_type=event.get('event_type', 'general'), status='success').inc()
        return {"status": "logged"}
    except Exception as e:
        events_processed_total.labels(event_type=event.get('event_type', 'general'), status='error').inc()
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)

