
import logging
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

# Ensure there’s at least one handler
if not root.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import json
import telebot
from src.drahmbot import Drahmbot

# -----------------------------
# AWS Lambda handler
# -----------------------------
def lambda_handler(event, context):
    logger.info("Lambda invoked")
    logger.info("Received event: %s", event)

    bot_instance = Drahmbot()  # always returns the singleton
    logger.info("Drahmbot instance retrieved")

    if "body" in event:
        try:
            logger.info("Processing update from event body")
            bot_instance.process_update(event["body"])
            logger.info("Update processed successfully")
        except Exception as e:
            logger.exception("Error processing update")  # logs stack trace

    else:
        logger.warning("No 'body' in event; nothing to process")

    logger.info("Lambda execution finished, returning response")
    return {
        "statusCode": 200,
        "body": json.dumps("ok")
    }

