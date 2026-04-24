import json
import logging
import asyncio
import os
import traceback
from src.drahmbot import Drahmbot

TELEGRAM_SECRET_HEADER = "x-telegram-bot-api-secret-token"

# Setup logging
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# -----------------------------
# AWS Lambda handler
# -----------------------------
async def handler(event, context):
    logger.info("Lambda invoked")
    logger.info("Received event: %s", event)

    # API Gateway calls carry 'headers'; EventBridge direct invocations don't
    # and are already authenticated via IAM.
    if "headers" in event:
        expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if expected:
            headers = event.get("headers") or {}
            provided = next(
                (v for k, v in headers.items() if k.lower() == TELEGRAM_SECRET_HEADER),
                None,
            )
            if provided != expected:
                logger.warning("Rejected webhook call: invalid or missing secret token")
                return {"statusCode": 401, "body": json.dumps("unauthorized")}

    bot_instance = Drahmbot()
    logger.info("Drahmbot instance retrieved")

    if "body" in event:
        try:
            # Ensure body is a dict, not a string
            body = event["body"]
            if isinstance(body, str):
                body = json.loads(body)

            # EventBridge fake payloads lack fields that telebot requires
            body.setdefault("update_id", 0)
            if isinstance(body.get("message"), dict):
                body["message"].setdefault("message_id", 0)
                body["message"].setdefault("date", 0)
                if isinstance(body["message"].get("chat"), dict):
                    body["message"]["chat"].setdefault("type", "group")

            logger.info("Processing update from event body")
            await bot_instance.process_update(body)
            logger.info("Update processed successfully")
        except Exception as e:
            logger.exception("Error processing update")
            try:
                dev_chat_id = bot_instance.dev_chat_id
                if dev_chat_id:
                    tb = traceback.format_exc()
                    if len(tb) > 3900:
                        tb = tb[:3900] + "\n…truncated"
                    msg = f"⚠️ Error processing update:\n\n<pre>{tb}</pre>"
                    await bot_instance.bot.send_message(dev_chat_id, msg, parse_mode="HTML")
            except Exception:
                logger.exception("Failed to send error notification to dev chat")
    else:
        logger.warning("No 'body' in event; nothing to process")

    logger.info("Lambda execution finished, returning response")
    return {
        "statusCode": 200,
        "body": json.dumps("ok")  
    }

# Explicitly use asyncio to run the async Lambda handler in case the environment doesn't do it automatically.
def lambda_handler(event, context):
    # This explicitly runs the asyncio event loop and awaits the coroutine
    return asyncio.run(handler(event, context))

