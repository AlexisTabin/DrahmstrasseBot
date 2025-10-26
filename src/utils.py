import os
import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)

def get_token():
    token = os.environ.get('TELEGRAM_TOKEN')
    if token:
        logger.info("Retrieved TELEGRAM_TOKEN from environment")
    else:
        logger.warning("TELEGRAM_TOKEN not found in environment")
    return token

def get_group_id():
    group_id = os.environ.get('BOT_CHAT_ID')
    if group_id:
        logger.info("Retrieved BOT_CHAT_ID from environment: %s", group_id)
    else:
        logger.warning("BOT_CHAT_ID not found in environment")
    return group_id

def is_even_week():
    week_number = datetime.datetime.now().isocalendar()[1]
    even = week_number % 2 == 0
    logger.info("Current week number: %d, even_week: %s", week_number, even)
    return even

