output "s3_input_bucket" {
  value = aws_s3_bucket.input.bucket
}

output "s3_output_bucket" {
  value = aws_s3_bucket.output.bucket
}

output "s3_models_bucket" {
  value = aws_s3_bucket.models.bucket
}

output "aws_access_key_id" {
  value = aws_iam_access_key.app_user.id
  sensitive = true
}

output "aws_secret_access_key" {
  value = aws_iam_access_key.app_user.secret
  sensitive = true
}

output "aws_region" {
  value = var.aws_region
}

output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    input  = aws_s3_bucket.input.bucket
    output = aws_s3_bucket.output.bucket
    models = aws_s3_bucket.models.bucket
  }
}

output "iam_access_key" {
  description = "IAM access key for application"
  value       = aws_iam_access_key.app_user.id
}

output "iam_secret_key" {
  description = "IAM secret key for application"
  value       = aws_iam_access_key.app_user.secret
  sensitive   = true
}

output "rabbitmq_endpoint" {
  description = "RabbitMQ broker endpoint"
  value       = aws_mq_broker.rabbitmq.instances[0].endpoints[0]
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "prometheus_url" {
  value = "http://${aws_lb.main.dns_name}:9090"
}

output "grafana_url" {
  value = "http://${aws_lb.main.dns_name}:3000"
}

output "domain_urls" {
  description = "Application URLs"
  value = {
    main       = var.create_certificate ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
    api        = var.create_certificate ? "https://api.${var.domain_name}" : "http://${aws_lb.main.dns_name}:8080"
    grafana    = var.create_certificate ? "https://grafana.${var.domain_name}" : "http://${aws_lb.main.dns_name}:3000"
    prometheus = var.create_certificate ? "https://prometheus.${var.domain_name}" : "http://${aws_lb.main.dns_name}:9090"
  }
}

output "ssl_certificate_arn" {
  value = var.create_certificate ? aws_acm_certificate.main[0].arn : null
}
