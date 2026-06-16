variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "drahmsstrasseTelegramBot"
}

variable "bot_chat_id" {
  description = "Telegram group chat ID"
  type        = string
}

variable "telegram_token" {
  description = "Telegram bot API token"
  type        = string
  sensitive   = true
}

variable "telegram_webhook_secret" {
  description = "Shared secret used as Telegram's webhook secret_token — verified on every inbound webhook call"
  type        = string
  sensitive   = true
}

variable "alert_email" {
  description = "Email address that receives AWS Budget and CloudWatch alarm notifications"
  type        = string
}
