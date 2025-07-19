import os

class Config:
    # AWS/S3 Configuration
    AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # S3 Buckets
    S3_INPUT_BUCKET = 'ai-upscaler-input'
    S3_OUTPUT_BUCKET = 'ai-upscaler-output'
    S3_MODELS_BUCKET = 'ai-upscaler-models'
    
    # Lambda Functions
    UPSCALER_LAMBDA_FUNCTION = 'ai-upscaler-worker'
    
    # RabbitMQ Configuration
    RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://admin:admin123@localhost:5672/')
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Analytics Service
    ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://localhost:8081')
    
    # Cognito Configuration
    COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', 'local_pool')
    COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', 'local_client')
    COGNITO_REGION = AWS_DEFAULT_REGION
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')



