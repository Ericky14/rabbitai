variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "rabbitai"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "rabbitmq_password" {
  description = "Password for RabbitMQ admin user"
  type        = string
  sensitive   = true
  default     = "admin123123123"
}

variable "grafana_password" {
  description = "Password for Grafana admin user"
  type        = string
  sensitive   = true
  default     = "admin123"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "fastrabbitai.com"
}

variable "create_certificate" {
  description = "Whether to create SSL certificate"
  type        = bool
  default     = true
}

variable "google_client_id" {
  description = "Google OAuth Client ID for authentication"
  type        = string
  sensitive   = true
}
