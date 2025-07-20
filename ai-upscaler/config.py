import os

class Config:
    # AWS/S3 Configuration
    AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # S3 Buckets
    S3_INPUT_BUCKET = os.getenv('S3_INPUT_BUCKET', 'ai-upscaler-input')
    S3_OUTPUT_BUCKET = os.getenv('S3_OUTPUT_BUCKET', 'ai-upscaler-output')
    S3_MODELS_BUCKET = os.getenv('S3_MODELS_BUCKET', 'ai-upscaler-models')
    
    # Upscaler Service
    UPSCALER_SERVICE_URL = os.getenv('UPSCALER_SERVICE_URL', 'http://upscaler-service:8083')
    
    # RabbitMQ Configuration
    RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://admin:admin123@localhost:5672/')
    
    # Remove AUTH_SERVICE_URL
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')




