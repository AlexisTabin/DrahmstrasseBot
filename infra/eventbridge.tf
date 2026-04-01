locals {
  prod_chat_id = "-1001633433047"
  dev_chat_id  = "-4867763410"

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
      description = "Paper reminder (Monday 19:00 UTC)"
      command     = "/papier@DrahmstrasseBot"
    }
    carton = {
      schedule    = "cron(0 19 ? * WED *)"
      description = "Carton reminder (Wednesday 19:00 UTC)"
      command     = "/carton@DrahmstrasseBot"
    }
    reminder = {
      schedule    = "cron(0 8 ? * THU *)"
      description = "Chore reminder (Thursday 08:00 UTC)"
      command     = "/reminder@DrahmstrasseBot"
    }
    recap = {
      schedule    = "cron(0 19 ? * SUN *)"
      description = "Weekly chore recap (Sunday 19:00 UTC)"
      command     = "/recap@DrahmstrasseBot"
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

resource "aws_cloudwatch_event_rule" "carton" {
  name                = "carton"
  description         = local.schedules.carton.description
  schedule_expression = local.schedules.carton.schedule
}

resource "aws_cloudwatch_event_target" "carton" {
  rule = aws_cloudwatch_event_rule.carton.name
  arn  = aws_lambda_function.bot.arn

  input = jsonencode({
    body = jsonencode({
      message = {
        chat = { id = tonumber(local.prod_chat_id) }
        text = local.schedules.carton.command
        entities = [{ type = "bot_command", offset = 0, length = length(local.schedules.carton.command) }]
      }
    })
  })
}

resource "aws_cloudwatch_event_rule" "reminder" {
  name                = "reminder"
  description         = local.schedules.reminder.description
  schedule_expression = local.schedules.reminder.schedule
}

resource "aws_cloudwatch_event_target" "reminder" {
  rule = aws_cloudwatch_event_rule.reminder.name
  arn  = aws_lambda_function.bot.arn

  input = jsonencode({
    body = jsonencode({
      message = {
        chat = { id = tonumber(local.dev_chat_id) }
        text = local.schedules.reminder.command
        entities = [{ type = "bot_command", offset = 0, length = length(local.schedules.reminder.command) }]
      }
    })
  })
}

resource "aws_cloudwatch_event_rule" "recap" {
  name                = "recap"
  description         = local.schedules.recap.description
  schedule_expression = local.schedules.recap.schedule
}

resource "aws_cloudwatch_event_target" "recap" {
  rule = aws_cloudwatch_event_rule.recap.name
  arn  = aws_lambda_function.bot.arn

  input = jsonencode({
    body = jsonencode({
      message = {
        chat = { id = tonumber(local.dev_chat_id) }
        text = local.schedules.recap.command
        entities = [{ type = "bot_command", offset = 0, length = length(local.schedules.recap.command) }]
      }
    })
  })
}
