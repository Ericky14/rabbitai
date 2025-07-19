from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Lambda execution metrics
lambda_invocations_total = Counter(
    'lambda_invocations_total',
    'Total number of Lambda invocations',
    ['function_name', 'status']
)

lambda_duration_seconds = Histogram(
    'lambda_duration_seconds',
    'Lambda execution duration in seconds',
    ['function_name']
)

lambda_errors_total = Counter(
    'lambda_errors_total',
    'Total number of Lambda errors',
    ['function_name', 'error_type']
)

# RabbitMQ metrics
rabbitmq_messages_published_total = Counter(
    'rabbitmq_messages_published_total',
    'Total messages published to RabbitMQ',
    ['queue']
)

rabbitmq_messages_consumed_total = Counter(
    'rabbitmq_messages_consumed_total',
    'Total messages consumed from RabbitMQ',
    ['queue']
)

# API metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

# File processing metrics
file_uploads_total = Counter(
    'file_uploads_total',
    'Total file uploads',
    ['file_type']
)

file_processing_duration_seconds = Histogram(
    'file_processing_duration_seconds',
    'File processing duration in seconds',
    ['operation']
)

class MetricsCollector:
    @staticmethod
    def record_lambda_invocation(function_name: str, duration: float, status: str):
        lambda_invocations_total.labels(function_name=function_name, status=status).inc()
        lambda_duration_seconds.labels(function_name=function_name).observe(duration)
    
    @staticmethod
    def record_lambda_error(function_name: str, error_type: str):
        lambda_errors_total.labels(function_name=function_name, error_type=error_type).inc()
    
    @staticmethod
    def record_rabbitmq_publish(queue: str):
        rabbitmq_messages_published_total.labels(queue=queue).inc()
    
    @staticmethod
    def record_api_request(method: str, endpoint: str, duration: float, status: int):
        api_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        api_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_file_upload(file_type: str):
        file_uploads_total.labels(file_type=file_type).inc()

metrics = MetricsCollector()