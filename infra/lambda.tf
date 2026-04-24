resource "aws_lambda_function" "bot" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.main.lambda_handler"
  runtime       = "python3.12"
  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 10

  filename = "dummy.zip"

  environment {
    variables = {
      TELEGRAM_TOKEN          = var.telegram_token
      BOT_CHAT_ID             = var.bot_chat_id
      DEV_CHAT_ID             = local.dev_chat_id
      DYNAMODB_TABLE          = aws_dynamodb_table.chores.name
      TELEGRAM_WEBHOOK_SECRET = var.telegram_webhook_secret
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash, last_modified]
  }
}

# Allow API Gateway to invoke the Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook.execution_arn}/*/*"
}

# Allow EventBridge rules to invoke the Lambda
resource "aws_lambda_permission" "eventbridge_whoishere" {
  statement_id  = "AllowEventBridgeWhoishere"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.whoishere.arn
}

resource "aws_lambda_permission" "eventbridge_roles" {
  statement_id  = "AllowEventBridgeRoles"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.roles.arn
}

resource "aws_lambda_permission" "eventbridge_papier" {
  statement_id  = "AllowEventBridgePapier"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.papier.arn
}

resource "aws_lambda_permission" "eventbridge_carton" {
  statement_id  = "AllowEventBridgeCarton"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.carton.arn
}

resource "aws_lambda_permission" "eventbridge_reminder" {
  statement_id  = "AllowEventBridgeReminder"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.reminder.arn
}

resource "aws_lambda_permission" "eventbridge_recap" {
  statement_id  = "AllowEventBridgeRecap"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.recap.arn
}
