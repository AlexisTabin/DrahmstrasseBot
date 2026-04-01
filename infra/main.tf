terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "drahmstrassebot-tfstate"
    key            = "infra/terraform.tfstate"
    region         = "eu-north-1"
    dynamodb_table = "drahmstrassebot-tflock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}
