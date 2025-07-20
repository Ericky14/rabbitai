from prometheus_client import Counter, Histogram, Gauge

# Define metrics
api_requests_total = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
api_request_duration_seconds = Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
file_uploads_total = Counter('file_uploads_total', 'Total file uploads', ['file_type'])

class MetricsCollector:
    @staticmethod
    def record_api_request(method: str, endpoint: str, duration: float, status: int):
        api_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        api_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_file_upload(file_type: str):
        file_uploads_total.labels(file_type=file_type).inc()

metrics = MetricsCollector()
