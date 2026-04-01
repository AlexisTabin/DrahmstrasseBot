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
