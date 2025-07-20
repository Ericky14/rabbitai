terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Buckets
resource "aws_s3_bucket" "input" {
  bucket = "${var.project_name}-input-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "output" {
  bucket = "${var.project_name}-output-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "models" {
  bucket = "${var.project_name}-models-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Lambda execution role
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.input.arn}/*",
          "${aws_s3_bucket.output.arn}/*",
          "${aws_s3_bucket.models.arn}/*"
        ]
      }
    ]
  })
}

# ECR Repository for Lambda
resource "aws_ecr_repository" "lambda_repo" {
  name = "${var.project_name}-lambda"
}

# Lambda function
resource "aws_lambda_function" "upscaler" {
  function_name = "${var.project_name}-worker"
  role         = aws_iam_role.lambda_role.arn
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda_repo.repository_url}:latest"
  timeout      = 300
  memory_size  = 2048

  environment {
    variables = {
      S3_INPUT_BUCKET  = aws_s3_bucket.input.bucket
      S3_OUTPUT_BUCKET = aws_s3_bucket.output.bucket
      S3_MODELS_BUCKET = aws_s3_bucket.models.bucket
    }
  }

  depends_on = [aws_iam_role_policy.lambda_policy]
}