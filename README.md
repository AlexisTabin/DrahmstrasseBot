# DrahmstrasseBot

[![Deploy](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/deploy.yml/badge.svg)](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/deploy.yml)
[![Infrastructure](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/infra.yml/badge.svg)](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/infra.yml)

Telegram bot for a shared flat — handles chore assignments, dinner polls, and recycling reminders.

## Bot Commands

| Command | Schedule | Description |
|---|---|---|
| `/roles` | Monday 08:00 UTC | Assigns weekly chore roles |
| `/papier` | Monday 19:00 UTC | Paper/cardboard recycling reminder |
| `/whoishere` | Weekdays 15:00 UTC | Dinner attendance poll |
| `/lessive` | Manual | Laundry card info |

## Architecture

- **Runtime**: Python 3.12 on AWS Lambda (x86_64)
- **Webhook**: API Gateway HTTP API → `POST /webhook` → Lambda
- **Scheduled triggers**: EventBridge rules invoke the Lambda with fake Telegram payloads
- **Secrets**: Telegram token stored in SSM Parameter Store
- **Infrastructure**: Managed with Terraform (`infra/`)

## Deployment

Code and infrastructure are deployed separately via GitHub Actions:

- **Code** (`deploy.yml`): Triggered on push to `master` (excluding `infra/`). Lints, tests, packages, and deploys to Lambda.
- **Infrastructure** (`infra.yml`): Triggered on changes to `infra/`. Runs `terraform plan` on PRs, `terraform apply` on merge to `master`.

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS credentials for deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for deployment |
| `BOT_CHAT_ID` | Telegram group chat ID |
| `TELEGRAM_TOKEN` | Telegram bot API token |

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```
