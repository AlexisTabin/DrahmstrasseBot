data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "drahmsstrasseTelegramBot-role-4xqq5pf3"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "ssm_read" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.telegram_token.arn]
  }
}

resource "aws_iam_role_policy" "ssm_read" {
  name   = "ssm-read-telegram-token"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.ssm_read.json
}

data "aws_iam_policy_document" "dynamodb_chores" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [aws_dynamodb_table.chores.arn]
  }
}

resource "aws_iam_role_policy" "dynamodb_chores" {
  name   = "dynamodb-chores"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.dynamodb_chores.json
}
