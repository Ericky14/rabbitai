#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Exit if an undefined variable is used
set -o pipefail  # Exit if any command in a pipeline fails

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found in root directory"
fi

# AWS Configuration
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?'AWS_ACCOUNT_ID is not set'}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
PROJECT_NAME="${PROJECT_NAME:-rabbitai}"

echo "Using AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "Using AWS Region: ${AWS_REGION}"

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Create ECR repositories if they don't exist
echo "Creating ECR repositories..."
aws ecr create-repository --repository-name rabbitai-ai-upscaler-api --region ${AWS_REGION} || true
aws ecr create-repository --repository-name rabbitai-upscaler-service --region ${AWS_REGION} || true

# Build and push AI Upscaler API
echo "Building and pushing AI Upscaler API..."
docker build -t ai-upscaler-api ./ai-upscaler
docker tag ai-upscaler-api:latest ${ECR_REGISTRY}/rabbitai-ai-upscaler-api:latest
docker push ${ECR_REGISTRY}/rabbitai-ai-upscaler-api:latest

# Build and push Upscaler Service
echo "Building and pushing Upscaler Service..."
docker build -t upscaler-service ./upscaler-service
docker tag upscaler-service:latest ${ECR_REGISTRY}/rabbitai-upscaler-service:latest
docker push ${ECR_REGISTRY}/rabbitai-upscaler-service:latest

# Build frontend
echo "Building frontend..."
cd frontend
npm run build
cd ..

# Upload frontend to S3
echo "Uploading frontend to S3..."
aws s3 sync frontend/build/ s3://${PROJECT_NAME}-frontend --delete

# Invalidate CloudFront cache
echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation --distribution-id $(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='${PROJECT_NAME}-frontend'].Id" --output text) --paths "/*"

echo "All images pushed successfully!"
echo "ECR Images:"
echo "- ${ECR_REGISTRY}/rabbitai-ai-upscaler-api:latest"
echo "- ${ECR_REGISTRY}/rabbitai-upscaler-service:latest"
