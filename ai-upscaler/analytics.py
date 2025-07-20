import json
from config import Config

class AnalyticsClient:
    def __init__(self):
        self.rabbitmq_url = Config.RABBITMQ_URL
    
    async def log_upscale_request(self, user_id: str, job_id: str, file_size: int, file_type: str):
        """Log upscale request via message queue"""
        event = {
            'event_type': 'upscale_request',
            'user_id': user_id,
            'job_id': job_id,
            'file_size': file_size,
            'file_type': file_type
        }
        await self._publish_event(event)
    
    async def log_upscale_completion(self, job_id: str, processing_time: float, status: str):
        """Log upscale completion via message queue"""
        event = {
            'event_type': 'upscale_completion',
            'job_id': job_id,
            'processing_time_seconds': processing_time,
            'status': status
        }
        await self._publish_event(event)
    
    async def _publish_event(self, event: dict):
        """Publish event to RabbitMQ"""
        try:
            # For now, just log the event
            print(f"Analytics event: {json.dumps(event)}")
        except Exception as e:
            print(f"Failed to publish analytics event: {e}")

analytics_client = AnalyticsClient()
