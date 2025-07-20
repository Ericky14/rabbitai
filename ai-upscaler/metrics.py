from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Define metrics with proper labels
api_requests_total = Counter(
    'api_requests_total', 
    'Total API requests', 
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds', 
    'API request duration', 
    ['method', 'endpoint']
)

file_uploads_total = Counter(
    'file_uploads_total', 
    'Total file uploads', 
    ['file_type']
)

# Add analytics metrics from analytics.py
analytics_events_processed_total = Counter(
    'analytics_events_processed_total',
    'Total analytics events processed',
    ['event_type', 'status']
)

class MetricsCollector:
    @staticmethod
    def record_api_request(method: str, endpoint: str, duration: float, status: int):
        api_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        api_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_file_upload(file_type: str):
        file_uploads_total.labels(file_type=file_type).inc()
    
    @staticmethod
    def record_analytics_event(event_type: str, status: str = "success"):
        analytics_events_processed_total.labels(event_type=event_type, status=status).inc()

metrics = MetricsCollector()
