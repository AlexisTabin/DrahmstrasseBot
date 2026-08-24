import datetime
import logging
import os

import boto3

logger = logging.getLogger(__name__)

# Reuses the chores table under a distinct row per week ("chiffons:2026-W14"),
# same trick as cendrier.py and plants.py, so chores._aggregate_completions's
# chore-parsing ignores these rows naturally and buckets them by key prefix.
#
# Unlike every chore subtask this one hangs off no role at all, and unlike
# /cendrier it belongs to nobody in particular: washing the used rags and tea
# towels is an occasional job anyone can pick up. It's optional too, so it
# never shows up in /recap or /reminder and can't make a week look unfinished.
CHIFFONS_KEY_PREFIX = "chiffons:"

# How far back get_last_done() looks for the previous wash. One get_item per
# week (same bounded-lookback trick as plants.get_last_watered_date), so keep
# it small: past this horizon the answer is just "ça fait un bail".
LOOKBACK_WEEKS = 8

_table = None


def _get_table():
    global _table
    if _table is None:
        table_name = os.environ.get("DYNAMODB_TABLE", "drahmstrassebot-chores")
        dynamodb = boto3.resource("dynamodb")
        _table = dynamodb.Table(table_name)
        logger.info("Initialized DynamoDB table (chiffons): %s", table_name)
    return _table


def _week_key(monday: datetime.date) -> str:
    iso = monday.isocalendar()
    return f"{CHIFFONS_KEY_PREFIX}{iso[0]}-W{iso[1]:02d}"


def _current_week_key() -> str:
    return _week_key(datetime.date.today())


def get_week_state() -> dict:
    """Return this week's chiffons record, or {} if nobody did it.

    Format when set: {"by": person, "at": iso_ts}
    """
    table = _get_table()
    response = table.get_item(Key={"week_key": _current_week_key()})
    item = response.get("Item", {})
    return item.get("chiffons", {})


def get_last_done(lookback_weeks: int = LOOKBACK_WEEKS):
    """Most recent *past* week the chiffons were washed, as
    (weeks_ago, state), or None if there's none within the lookback window.

    This week is skipped on purpose: get_week_state already answers for it,
    and what the message wants here is "and before that?".
    """
    table = _get_table()
    today = datetime.date.today()
    for weeks_ago in range(1, lookback_weeks + 1):
        key = _week_key(today - datetime.timedelta(weeks=weeks_ago))
        response = table.get_item(Key={"week_key": key})
        state = response.get("Item", {}).get("chiffons", {})
        if state:
            return weeks_ago, state
    return None


def toggle_week_state(person: str) -> dict:
    """Toggle this week's chiffons mark. Clears it if already set; otherwise
    records `person` as having washed them. Returns the new state (empty dict
    if cleared).
    """
    table = _get_table()
    current = get_week_state()
    if current:
        table.update_item(
            Key={"week_key": _current_week_key()},
            UpdateExpression="REMOVE chiffons",
        )
        logger.info("Chiffons cleared by %s key=%s", person, _current_week_key())
        return {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = {"by": person, "at": now}
    table.update_item(
        Key={"week_key": _current_week_key()},
        UpdateExpression="SET chiffons = :val",
        ExpressionAttributeValues={":val": state},
    )
    logger.info("Chiffons set: by=%s key=%s", person, _current_week_key())
    return state
