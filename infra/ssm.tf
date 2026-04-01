resource "aws_ssm_parameter" "telegram_token" {
  name  = "/drahmstrassebot/telegram-token"
  type  = "SecureString"
  value = var.telegram_token

  lifecycle {
    ignore_changes = [value]
  }
}
