import datetime
import logging
import os

import boto3

logger = logging.getLogger(__name__)

STATE_WATERED = "watered"
# Legacy value: pre-revision rows stored "needs" with the same intent (someone
# clicked the only meaningful button of the day). Still counts as a watered
# day when computing the warm-band cooldown.
_LEGACY_WATERED_STATE = "needs"
_WATERED_STATES = frozenset({STATE_WATERED, _LEGACY_WATERED_STATE})

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


def is_watered(state_data: dict) -> bool:
    """True if the given watering row marks the day as watered (incl. legacy)."""
    return state_data.get("state") in _WATERED_STATES


def get_today_state() -> dict:
    """Return today's watering record, or empty dict if no one has clicked yet.

    Format when set: {"state": "watered", "by": person, "at": iso_ts}
    """
    table = _get_table()
    response = table.get_item(Key={"week_key": today_key()})
    item = response.get("Item", {})
    return item.get("watering", {})


def get_last_watered_date(lookback_days: int = 5):
    """Most recent date in the last `lookback_days` where someone marked the
    plants as watered. Accepts both the current `"watered"` state and the
    legacy `"needs"` value so pre-revision rows still count. Returns None if
    no such row is found in the window.
    """
    table = _get_table()
    today = datetime.date.today()
    for offset in range(lookback_days + 1):
        date = today - datetime.timedelta(days=offset)
        key = f"{PLANT_KEY_PREFIX}{date.isoformat()}"
        response = table.get_item(Key={"week_key": key})
        watering = response.get("Item", {}).get("watering", {})
        if is_watered(watering):
            return date
    return None


def toggle_today_state(person: str) -> dict:
    """Toggle today's watered mark. If already watered, clear it; otherwise
    set it to `STATE_WATERED` by `person`. Returns the new state dict (empty
    if cleared).
    """
    table = _get_table()
    current = get_today_state()
    if is_watered(current):
        table.update_item(
            Key={"week_key": today_key()},
            UpdateExpression="REMOVE watering",
        )
        logger.info("Plant watering cleared by %s key=%s", person, today_key())
        return {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    watering = {"state": STATE_WATERED, "by": person, "at": now}
    table.update_item(
        Key={"week_key": today_key()},
        UpdateExpression="SET watering = :val",
        ExpressionAttributeValues={":val": watering},
    )
    logger.info("Plant watering set: by=%s key=%s", person, today_key())
    return watering
