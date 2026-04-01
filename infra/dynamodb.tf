resource "aws_dynamodb_table" "chores" {
  name         = "drahmstrassebot-chores"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "week_key"

  attribute {
    name = "week_key"
    type = "S"
  }
}
