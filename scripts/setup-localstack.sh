#!/bin/bash

set -e  # Exit on any error

echo "=== Starting LocalStack Setup ==="

# Determine the LocalStack endpoint based on environment
if [ -n "$LOCALSTACK_HOSTNAME" ]; then
    LOCALSTACK_ENDPOINT="http://${LOCALSTACK_HOSTNAME}:4566"
else
    LOCALSTACK_ENDPOINT="http://localhost:4566"
fi

echo "Using LocalStack endpoint: $LOCALSTACK_ENDPOINT"

# Set dummy AWS credentials for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Wait for LocalStack to be ready by trying to list buckets
echo "Waiting for LocalStack S3 to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

until aws --endpoint-url=${LOCALSTACK_ENDPOINT} s3 ls > /dev/null 2>&1; do
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
aws --endpoint-url=${LOCALSTACK_ENDPOINT} s3 mb s3://ai-upscaler-input || echo "Bucket ai-upscaler-input already exists"
aws --endpoint-url=${LOCALSTACK_ENDPOINT} s3 mb s3://ai-upscaler-output || echo "Bucket ai-upscaler-output already exists"
aws --endpoint-url=${LOCALSTACK_ENDPOINT} s3 mb s3://ai-upscaler-models || echo "Bucket ai-upscaler-models already exists"
echo "✓ S3 buckets created"

# Verify buckets were created
echo "Verifying S3 buckets:"
aws --endpoint-url=${LOCALSTACK_ENDPOINT} s3 ls

echo "=== LocalStack setup complete! ==="
echo "Services available:"
echo "  - S3 buckets: ai-upscaler-input, ai-upscaler-output, ai-upscaler-models"
echo "  - Endpoint: ${LOCALSTACK_ENDPOINT}"

