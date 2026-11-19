variable "region" {
  description = "AWS region. eu-west-1 because Rekognition is not available in af-south-1."
  type        = string
  default     = "eu-west-1"
}

variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
  default     = "kuda"
}

variable "similarity_threshold" {
  description = "Minimum Rekognition similarity (%) for a KYC face match."
  type        = number
  default     = 80

  validation {
    condition     = var.similarity_threshold > 0 && var.similarity_threshold <= 100
    error_message = "similarity_threshold must be between 0 and 100."
  }
}

variable "high_risk_threshold_ngn" {
  description = "Transactions at or above this amount (NGN) are flagged for review."
  type        = number
  default     = 500000
}

variable "fraud_alert_email" {
  description = "Optional email address subscribed to fraud alerts. AWS sends a confirmation email first."
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for Lambda and Step Functions logs."
  type        = number
  default     = 14
}
