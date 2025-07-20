#!/bin/bash

set -e  # Exit on any error

echo "=== Starting LocalStack Setup ==="

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "running"'; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: LocalStack failed to start after $MAX_RETRIES attempts"
    exit 1
  fi
  echo "Attempt $RETRY_COUNT/$MAX_RETRIES - LocalStack not ready yet..."
  sleep 2
done

echo "✓ LocalStack is ready!"

# Set dummy AWS credentials for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Create S3 buckets
echo "Creating S3 buckets..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-upscaler-input || echo "Bucket ai-upscaler-input already exists"
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-upscaler-output || echo "Bucket ai-upscaler-output already exists"
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-upscaler-models || echo "Bucket ai-upscaler-models already exists"
echo "✓ S3 buckets created"

echo "=== LocalStack setup complete! ==="
echo "Services available:"
echo "  - S3 buckets: ai-upscaler-input, ai-upscaler-output, ai-upscaler-models"
echo "  - Upscaler service: http://localhost:8083"

