import json
import logging
import asyncio
from src.drahmbot import Drahmbot

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
    bot_instance = Drahmbot()
    logger.info("Drahmbot instance retrieved")

    if "body" in event:
        try:
            # Ensure body is a dict, not a string
            body = event["body"]
            if isinstance(body, str):
                body = json.loads(body)

            logger.info("Processing update from event body")
            await bot_instance.process_update(body)
            logger.info("Update processed successfully")
        except Exception as e:
            logger.exception("Error processing update")
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

