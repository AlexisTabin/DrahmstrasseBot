import datetime
import logging
import os

import boto3

logger = logging.getLogger(__name__)

STATE_NEEDS_WATER = "needs"
STATE_OK = "ok"
VALID_STATES = (STATE_NEEDS_WATER, STATE_OK)

# Reuses the chores table. The key field is named `week_key` but DynamoDB
# treats it as an opaque string. Prefix `plant:` keeps these rows distinct
# from chore rows (`2026-W14`) so `chores.get_stats` ignores them naturally.
PLANT_KEY_PREFIX = "plant:"

_table = None


def _get_table():
    global _table
    if _table is None:
        table_name = os.environ.get("DYNAMODB_TABLE", "drahmstrassebot-chores")
        dynamodb = boto3.resource("dynamodb")
        _table = dynamodb.Table(table_name)
        logger.info("Initialized DynamoDB table (plants): %s", table_name)
    return _table


def today_key() -> str:
    return f"{PLANT_KEY_PREFIX}{datetime.date.today().isoformat()}"


def get_today_state() -> dict:
    """Return today's watering state, or empty dict if no one has voted yet.

    Format: {"state": "needs"|"ok", "by": person, "at": iso_ts}
    """
    table = _get_table()
    response = table.get_item(Key={"week_key": today_key()})
    item = response.get("Item", {})
    return item.get("watering", {})


def get_last_watered_date(lookback_days: int = 5):
    """Most recent date in the last `lookback_days` where someone clicked
    'faut arroser' (state == 'needs'), which we treat as a commitment that
    plants got watered that day. Returns None if no such row is found.
    """
    table = _get_table()
    today = datetime.date.today()
    for offset in range(lookback_days + 1):
        date = today - datetime.timedelta(days=offset)
        key = f"{PLANT_KEY_PREFIX}{date.isoformat()}"
        response = table.get_item(Key={"week_key": key})
        watering = response.get("Item", {}).get("watering", {})
        if watering.get("state") == STATE_NEEDS_WATER:
            return date
    return None


def set_today_state(state: str, person: str) -> dict:
    """Set today's watering state, overwriting any prior vote. Returns the new state."""
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state: {state}")
    table = _get_table()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    watering = {"state": state, "by": person, "at": now}
    table.update_item(
        Key={"week_key": today_key()},
        UpdateExpression="SET watering = :val",
        ExpressionAttributeValues={":val": watering},
    )
    logger.info("Plant watering: state=%s by=%s key=%s", state, person, today_key())
    return watering
