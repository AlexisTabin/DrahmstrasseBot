# Temporary import blocks — remove after first successful `terraform apply`

import {
  to = aws_lambda_function.bot
  id = "drahmsstrasseTelegramBot"
}

import {
  to = aws_iam_role.lambda_role
  id = "drahmsstrasseTelegramBot-role-4xqq5pf3"
}

import {
  to = aws_cloudwatch_event_rule.whoishere
  id = "whoishere"
}

import {
  to = aws_cloudwatch_event_rule.roles
  id = "roles"
}

import {
  to = aws_cloudwatch_event_rule.papier
  id = "papier"
}

import {
  to = aws_cloudwatch_event_target.whoishere
  id = "whoishere/4yb8lsapzf0so8ua5oif"
}

import {
  to = aws_cloudwatch_event_target.roles
  id = "roles/ctare3ag5n26f1jbbna"
}

import {
  to = aws_cloudwatch_event_target.papier
  id = "papier/st9ip73rj8i97ngvihc"
}

# API Gateway will be created fresh (no existing HTTP API found to import)
