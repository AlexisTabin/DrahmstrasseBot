import json
import telebot
import logging

from src.drahmbot import Drahmbot

# -----------------------------
# AWS Lambda handler
# -----------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Hello from Lambda!")

    bot_instance = Drahmbot()  # always returns the singleton
    if "body" in event:
        try:
            bot_instance.process_update(event["body"])
        except Exception as e:
            print(f"Error processing update: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps("ok")
    }

