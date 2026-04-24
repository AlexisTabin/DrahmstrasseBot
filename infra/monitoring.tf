resource "aws_sns_topic" "alerts" {
  name = "drahmstrassebot-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Fires when Lambda is invoked more than 50 times in 5 minutes — abuse signal.
# Normal traffic is a handful of invocations per window (EventBridge schedules + coloc messages).
resource "aws_cloudwatch_metric_alarm" "lambda_invocations_spike" {
  alarm_name          = "drahmstrassebot-invocations-spike"
  alarm_description   = "Lambda invoked >50 times in 5 minutes — possible abuse"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 50
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.bot.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_budgets_budget" "monthly_cost" {
  name         = "drahmstrassebot-monthly"
  budget_type  = "COST"
  limit_amount = "5"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
