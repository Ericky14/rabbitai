#!/bin/bash

set -e  # Exit on any error

echo "=== Starting LocalStack Setup ==="

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"'; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: LocalStack failed to start after $MAX_RETRIES attempts"
    exit 1
  fi
  echo "Attempt $RETRY_COUNT/$MAX_RETRIES - LocalStack not ready yet..."
  sleep 2
done

echo "✓ LocalStack is ready!"

# Create S3 buckets
echo "Creating S3 buckets..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-upscaler-input || echo "Bucket ai-upscaler-input already exists"
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-upscaler-output || echo "Bucket ai-upscaler-output already exists"
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-upscaler-models || echo "Bucket ai-upscaler-models already exists"
echo "✓ S3 buckets created"

# Create Lambda function
echo "Creating Lambda function..."
cd lambda-functions/upscaler
if [ ! -f "upscaler.zip" ]; then
  echo "Creating Lambda deployment package..."
  zip -r upscaler.zip . -x "*.pyc" "__pycache__/*"
else
  echo "Lambda package already exists, recreating..."
  rm upscaler.zip
  zip -r upscaler.zip . -x "*.pyc" "__pycache__/*"
fi

echo "Deploying Lambda function..."
aws --endpoint-url=http://localhost:4566 lambda create-function \
    --function-name ai-upscaler-worker \
    --runtime python3.9 \
    --role arn:aws:iam::123456789012:role/lambda-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://upscaler.zip \
    --timeout 300 \
    --memory-size 512 || echo "Lambda function already exists, updating..."

if [ $? -ne 0 ]; then
  echo "Function exists, updating code..."
  aws --endpoint-url=http://localhost:4566 lambda update-function-code \
      --function-name ai-upscaler-worker \
      --zip-file fileb://upscaler.zip
fi

cd ../..
echo "✓ Lambda function deployed"

# Create Cognito User Pool
echo "Creating Cognito User Pool..."
aws --endpoint-url=http://localhost:4566 cognito-idp create-user-pool \
    --pool-name ai-upscaler-users \
    --policies PasswordPolicy='{MinimumLength=8,RequireUppercase=false,RequireLowercase=false,RequireNumbers=false,RequireSymbols=false}' || echo "User pool already exists"
echo "✓ Cognito User Pool created"

echo "=== LocalStack setup complete! ==="
echo "Services available:"
echo "  - S3 buckets: ai-upscaler-input, ai-upscaler-output, ai-upscaler-models"
echo "  - Lambda: ai-upscaler-worker"
echo "  - Cognito: ai-upscaler-users"

