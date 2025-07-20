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
  value = aws_lb.main.dns_name
}

output "prometheus_url" {
  value = "http://${aws_lb.main.dns_name}:9090"
}

output "grafana_url" {
  value = "http://${aws_lb.main.dns_name}:3000"
}

output "domain_urls" {
  value = {
    main       = "https://${var.domain_name}"
    api        = "https://api.${var.domain_name}"
    grafana    = "https://grafana.${var.domain_name}:3001"
    prometheus = "https://prometheus.${var.domain_name}:9091"
    rabbitmq   = "https://rabbitmq.${var.domain_name}:15672"
  }
}

output "ssl_certificate_arn" {
  value = var.create_certificate ? aws_acm_certificate.main[0].arn : null
}
