import datetime
import logging
import os

import boto3

logger = logging.getLogger(__name__)

# Reuses the chores table under a distinct row per week ("cendrier:2026-W14")
# so it doesn't interfere with chores._aggregate_completions scanning plain
# chore rows ("2026-W14"). Standalone: unlike CUISINE/SDBs/SOLs/DÉCHETS this
# task never rotates and isn't part of /recap, /reminder, or /leaderboard.
CENDRIER_KEY_PREFIX = "cendrier:"

# Whoever is on the hook for /cendrier, regardless of chore-role rotation.
SMOKERS = {"Maël"}

_table = None


def _get_table():
    global _table
    if _table is None:
        table_name = os.environ.get("DYNAMODB_TABLE", "drahmstrassebot-chores")
        dynamodb = boto3.resource("dynamodb")
        _table = dynamodb.Table(table_name)
        logger.info("Initialized DynamoDB table (cendrier): %s", table_name)
    return _table


def _current_week_key() -> str:
    iso = datetime.date.today().isocalendar()
    return f"{CENDRIER_KEY_PREFIX}{iso[0]}-W{iso[1]:02d}"


def is_smoker(person: str) -> bool:
    """Whether this person is on the hook for the standalone cendrier task."""
    return person in SMOKERS


def get_week_state() -> dict:
    """Return this week's cendrier record, or {} if not yet marked.

    Format when set: {"by": person, "at": iso_ts}
    """
    table = _get_table()
    response = table.get_item(Key={"week_key": _current_week_key()})
    item = response.get("Item", {})
    return item.get("cendrier", {})


def toggle_week_state(person: str) -> dict:
    """Toggle this week's cendrier mark. Clears it if already set; otherwise
    records `person` as having emptied it. Returns the new state (empty dict
    if cleared).
    """
    table = _get_table()
    current = get_week_state()
    if current:
        table.update_item(
            Key={"week_key": _current_week_key()},
            UpdateExpression="REMOVE cendrier",
        )
        logger.info("Cendrier cleared by %s key=%s", person, _current_week_key())
        return {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = {"by": person, "at": now}
    table.update_item(
        Key={"week_key": _current_week_key()},
        UpdateExpression="SET cendrier = :val",
        ExpressionAttributeValues={":val": state},
    )
    logger.info("Cendrier set: by=%s key=%s", person, _current_week_key())
    return state
