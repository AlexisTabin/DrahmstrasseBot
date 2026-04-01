locals {
  prod_chat_id = "-1001633433047"

  schedules = {
    whoishere = {
      schedule    = "cron(0 15 ? * MON-FRI *)"
      description = "Ask who is home for dinner (weekdays 15:00 UTC)"
      command     = "/whoishere@DrahmstrasseBot"
    }
    roles = {
      schedule    = "cron(0 8 ? * MON *)"
      description = "Assign weekly chore roles (Monday 08:00 UTC)"
      command     = "/roles"
    }
    papier = {
      schedule    = "cron(0 19 ? * MON *)"
      description = "Paper/cardboard reminder (Monday 19:00 UTC)"
      command     = "/papier@DrahmstrasseBot"
    }
  }
}

resource "aws_cloudwatch_event_rule" "whoishere" {
  name                = "whoishere"
  description         = local.schedules.whoishere.description
  schedule_expression = local.schedules.whoishere.schedule
}

resource "aws_cloudwatch_event_target" "whoishere" {
  rule = aws_cloudwatch_event_rule.whoishere.name
  arn  = aws_lambda_function.bot.arn

  input = jsonencode({
    body = jsonencode({
      message = {
        chat = { id = tonumber(local.prod_chat_id) }
        text = local.schedules.whoishere.command
        entities = [{ type = "bot_command", offset = 0, length = length(local.schedules.whoishere.command) }]
      }
    })
  })
}

resource "aws_cloudwatch_event_rule" "roles" {
  name                = "roles"
  description         = local.schedules.roles.description
  schedule_expression = local.schedules.roles.schedule
}

resource "aws_cloudwatch_event_target" "roles" {
  rule = aws_cloudwatch_event_rule.roles.name
  arn  = aws_lambda_function.bot.arn

  input = jsonencode({
    body = jsonencode({
      message = {
        chat = { id = tonumber(local.prod_chat_id) }
        text = local.schedules.roles.command
        entities = [{ type = "bot_command", offset = 0, length = length(local.schedules.roles.command) }]
      }
    })
  })
}

resource "aws_cloudwatch_event_rule" "papier" {
  name                = "papier"
  description         = local.schedules.papier.description
  schedule_expression = local.schedules.papier.schedule
}

resource "aws_cloudwatch_event_target" "papier" {
  rule = aws_cloudwatch_event_rule.papier.name
  arn  = aws_lambda_function.bot.arn

  input = jsonencode({
    body = jsonencode({
      message = {
        chat = { id = tonumber(local.prod_chat_id) }
        text = local.schedules.papier.command
        entities = [{ type = "bot_command", offset = 0, length = length(local.schedules.papier.command) }]
      }
    })
  })
}
