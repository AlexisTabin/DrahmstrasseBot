# DrahmstrasseBot

[![Deploy](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/deploy.yml/badge.svg)](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/deploy.yml)
[![Infrastructure](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/infra.yml/badge.svg)](https://github.com/AlexisTabin/DrahmstrasseBot/actions/workflows/infra.yml)
[![codecov](https://codecov.io/gh/AlexisTabin/DrahmstrasseBot/branch/master/graph/badge.svg)](https://codecov.io/gh/AlexisTabin/DrahmstrasseBot)

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

## Request Flow

What happens when a user types a command in the Telegram chat:

```
  👤 User in Telegram chat
   │
   │ 1. types "/roles"
   ▼
  ┌─────────────────────────┐
  │    Telegram servers     │
  │   (api.telegram.org)    │
  └───────────┬─────────────┘
              │
              │ 2. POST update JSON to webhook URL
              │    header: X-Telegram-Bot-Api-Secret-Token  🔒 ②
              ▼
  ┌─────────────────────────┐
  │   AWS API Gateway       │
  │   POST /webhook         │
  │   (rate-limited)        │
  └───────────┬─────────────┘
              │
              │ 3. invoke
              ▼
  ┌─────────────────────────┐        ┌──────────────┐
  │   AWS Lambda            │ 4. r/w │  DynamoDB    │
  │   src.main.lambda_      │◀──────▶│  (chores     │
  │   handler               │        │   state)     │
  │                         │        └──────────────┘
  │   • verify secret 🔒 ②  │
  │   • dispatch /roles     │
  │   • build reply         │
  └───────────┬─────────────┘
              │
              │ 5. POST sendMessage
              │    URL: /bot<TELEGRAM_TOKEN>/sendMessage  🔒 ①
              ▼
  ┌─────────────────────────┐
  │    Telegram servers     │
  └───────────┬─────────────┘
              │
              │ 6. deliver reply
              ▼
  👤 User sees bot's answer
```

**Two secrets, two directions:**

- 🔒 ① `TELEGRAM_TOKEN` — Lambda → Telegram (outbound). Proves "this is my bot" when calling `sendMessage`, `setWebhook`, etc.
- 🔒 ② `secret_token` on `setWebhook` — Telegram → Lambda (inbound). Telegram sends it as the `X-Telegram-Bot-Api-Secret-Token` header on every webhook call; the Lambda rejects anything without it, so random traffic to the public API Gateway URL can't trigger bot logic.

