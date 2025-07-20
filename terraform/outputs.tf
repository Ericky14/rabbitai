output "s3_input_bucket" {
  value = aws_s3_bucket.input.bucket
}

output "s3_output_bucket" {
  value = aws_s3_bucket.output.bucket
}

output "s3_models_bucket" {
  value = aws_s3_bucket.models.bucket
}

output "lambda_function_name" {
  value = aws_lambda_function.upscaler.function_name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda_repo.repository_url
}