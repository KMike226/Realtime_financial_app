# Variables for Snowflake Data Warehouse MVP

variable "snowflake_account" {
  description = "Snowflake account identifier"
  type        = string
}

variable "snowflake_username" {
  description = "Snowflake username"
  type        = string
}

variable "snowflake_password" {
  description = "Snowflake password"
  type        = string
  sensitive   = true
}

variable "snowflake_role" {
  description = "Snowflake role to use"
  type        = string
  default     = "ACCOUNTADMIN"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for data ingestion"
  type        = string
}

variable "s3_role_arn" {
  description = "IAM role ARN for S3 access"
  type        = string
}
