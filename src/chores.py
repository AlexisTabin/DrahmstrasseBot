import os
import logging
import datetime
import boto3

logger = logging.getLogger(__name__)

_table = None


def _get_table():
    """Return a cached DynamoDB Table resource."""
    global _table
    if _table is None:
        table_name = os.environ.get("DYNAMODB_TABLE", "drahmstrassebot-chores")
        dynamodb = boto3.resource("dynamodb")
        _table = dynamodb.Table(table_name)
        logger.info("Initialized DynamoDB table: %s", table_name)
    return _table


def _current_week_key() -> str:
    """Return the ISO week key, e.g. '2026-W14'."""
    today = datetime.date.today()
    iso = today.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def mark_done(role: str, person: str) -> bool:
    """Mark a role as done for the current week.

    Returns True if newly marked, False if already done.
    """
    table = _get_table()
    week_key = _current_week_key()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Ensure the item and completed map exist (no-op if already present)
    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression="SET completed = if_not_exists(completed, :empty_map)",
        ExpressionAttributeValues={":empty_map": {}},
    )

    try:
        table.update_item(
            Key={"week_key": week_key},
            UpdateExpression="SET completed.#role = :val",
            ConditionExpression="attribute_not_exists(completed.#role)",
            ExpressionAttributeNames={"#role": role},
            ExpressionAttributeValues={
                ":val": {"by": person, "at": now}
            },
        )
        logger.info("Marked %s as done by %s for %s", role, person, week_key)
        return True
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.info("Role %s already marked done for %s", role, week_key)
        return False


def get_week_status(week_key: str = None) -> dict:
    """Get the completion status for a week. Returns the completed map (may be empty)."""
    table = _get_table()
    if week_key is None:
        week_key = _current_week_key()

    response = table.get_item(Key={"week_key": week_key})
    item = response.get("Item", {})
    return item.get("completed", {})


def get_thursday_reminder(role_assignments: dict) -> str:
    """Build a Thursday reminder listing pending tasks.

    Args:
        role_assignments: dict of {role: person} for the current week.
    """
    completed = get_week_status()
    pending = []
    done = []
    for role, person in role_assignments.items():
        if role in completed:
            done.append(f"  {role} ({person})")
        else:
            pending.append(f"  {role} ({person})")

    if not pending:
        return "Rappel du jeudi : tout est fait cette semaine, bravo !"

    lines = ["Rappel du jeudi — tâches pas encore faites :"]
    for item in pending:
        lines.append(f"  \u274c{item}")
    if done:
        lines.append("Déjà fait :")
        for item in done:
            lines.append(f"  \u2705{item}")
    return "\n".join(lines)


def get_sunday_recap(role_assignments: dict) -> str:
    """Build a Sunday recap of the week's chore status.

    Args:
        role_assignments: dict of {role: person} for the current week.
    """
    completed = get_week_status()
    lines = ["Récap de la semaine :"]
    for role, person in role_assignments.items():
        if role in completed:
            info = completed[role]
            lines.append(f"  \u2705 {role} ({person}) — fait par {info['by']}")
        else:
            lines.append(f"  \u274c {role} ({person}) — pas fait")
    return "\n".join(lines)
