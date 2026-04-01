output "webhook_url" {
  description = "API Gateway webhook URL for Telegram"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/webhook"
}

output "lambda_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.bot.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.bot.function_name
}

output "ssm_parameter_name" {
  description = "SSM parameter name for the Telegram token"
  value       = aws_ssm_parameter.telegram_token.name
}
