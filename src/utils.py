import os
import datetime

def get_token():
    return os.environ['TELEGRAM_TOKEN']

def get_group_id():
    return os.environ['BOT_CHAT_ID']

def is_even_week():
    week_number = datetime.datetime.now().isocalendar()[1]
    return week_number % 2 == 0

