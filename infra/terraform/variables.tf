variable "region" {
  description = "AWS region. ap-south-1 = Mumbai (data residency for Indian user data)."
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix for all resources."
  default     = "scamshield"
}

variable "retention_days" {
  description = "S3 lifecycle expiry for raw objects — PII is minimised by design."
  default     = 30
}
