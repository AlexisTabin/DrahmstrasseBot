import os
import logging
import datetime
import boto3

from src import phrases

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


def toggle_role(role: str, person: str) -> bool:
    """Toggle a simple role's completion. Returns True if now done."""
    table = _get_table()
    week_key = _current_week_key()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression="SET completed = if_not_exists(completed, :empty_map)",
        ExpressionAttributeValues={":empty_map": {}},
    )

    status = get_week_status(week_key)
    if role in status and "by" in status[role]:
        table.update_item(
            Key={"week_key": week_key},
            UpdateExpression="REMOVE completed.#role",
            ExpressionAttributeNames={"#role": role},
        )
        logger.info("Toggled %s OFF for %s", role, week_key)
        return False
    else:
        table.update_item(
            Key={"week_key": week_key},
            UpdateExpression="SET completed.#role = :val",
            ExpressionAttributeNames={"#role": role},
            ExpressionAttributeValues={":val": {"by": person, "at": now}},
        )
        logger.info("Toggled %s ON by %s for %s", role, person, week_key)
        return True


def toggle_subtask(role: str, subtask: str, person: str) -> bool:
    """Toggle a sub-task's completion. Returns True if now done."""
    table = _get_table()
    week_key = _current_week_key()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression="SET completed = if_not_exists(completed, :empty_map)",
        ExpressionAttributeValues={":empty_map": {}},
    )
    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression="SET completed.#role = if_not_exists(completed.#role, :empty_subtasks)",
        ExpressionAttributeNames={"#role": role},
        ExpressionAttributeValues={":empty_subtasks": {"subtasks": {}}},
    )

    status = get_week_status(week_key)
    role_data = status.get(role, {})
    subtasks = role_data.get("subtasks", {})

    if subtask in subtasks:
        table.update_item(
            Key={"week_key": week_key},
            UpdateExpression="REMOVE completed.#role.subtasks.#subtask",
            ExpressionAttributeNames={"#role": role, "#subtask": subtask},
        )
        logger.info("Toggled %s.%s OFF for %s", role, subtask, week_key)
        return False
    else:
        table.update_item(
            Key={"week_key": week_key},
            UpdateExpression="SET completed.#role.subtasks.#subtask = :val",
            ExpressionAttributeNames={"#role": role, "#subtask": subtask},
            ExpressionAttributeValues={":val": {"by": person, "at": now}},
        )
        logger.info("Toggled %s.%s ON by %s for %s", role, subtask, person, week_key)
        return True


def is_role_complete(role: str, completed_map: dict) -> bool:
    """Check if a role is fully completed, handling both old and new formats."""
    from src.menage import get_subtasks_for_role

    if role not in completed_map:
        return False

    role_data = completed_map[role]

    # Old format: {by, at}
    if "by" in role_data:
        return True

    # New format: {subtasks: {name: {by, at}, ...}}
    if "subtasks" in role_data:
        expected = get_subtasks_for_role(role)
        if expected is None:
            return False
        completed_subtasks = role_data["subtasks"]
        return all(s in completed_subtasks for s in expected)

    return False


def _pending_detail(role: str, completed: dict) -> str:
    """Return detail string for sub-task roles with missing items."""
    from src.menage import get_subtasks_for_role

    expected = get_subtasks_for_role(role)
    if expected is None:
        return ""

    role_data = completed.get(role, {})

    # Old format: {by, at} — no subtask detail to show
    if "by" in role_data:
        return ""

    completed_subtasks = role_data.get("subtasks", {})
    missing = [s for s in expected if s not in completed_subtasks]
    if missing:
        return f" [manque : {', '.join(missing)}]"
    return ""


def _who_did_it(role_data: dict) -> str:
    """Extract person name(s) from either format."""
    if "by" in role_data:
        return role_data["by"]
    if "subtasks" in role_data:
        names = set()
        for sub_data in role_data["subtasks"].values():
            if "by" in sub_data:
                names.add(sub_data["by"])
        return ", ".join(sorted(names)) if names else "?"
    return "?"


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
        if is_role_complete(role, completed):
            done.append(f"  {role} ({person})")
        else:
            detail = _pending_detail(role, completed)
            pending.append(f"  {role} ({person}){detail}")

    if not pending:
        return phrases.pick(phrases.THURSDAY_ALL_DONE)

    lines = [phrases.pick(phrases.THURSDAY_REMINDER_HEADER)]
    for item in pending:
        lines.append(f"  \u274c{item}")
    if done:
        lines.append(phrases.pick(phrases.THURSDAY_DONE_SECTION))
        for item in done:
            lines.append(f"  \u2705{item}")
    return "\n".join(lines)


def get_stats() -> str:
    """Aggregate chore completions across all weeks and return a formatted leaderboard."""
    table = _get_table()
    response = table.scan()
    items = response.get("Items", [])

    counts: dict[str, int] = {}
    for item in items:
        completed = item.get("completed", {})
        for role, role_data in completed.items():
            # Old format: {by, at}
            if "by" in role_data:
                person = role_data["by"]
                counts[person] = counts.get(person, 0) + 1
            # New format: {subtasks: {name: {by, at}, ...}}
            elif "subtasks" in role_data:
                if is_role_complete(role, completed):
                    names = set()
                    for sub_data in role_data["subtasks"].values():
                        if "by" in sub_data:
                            names.add(sub_data["by"])
                    for person in names:
                        counts[person] = counts.get(person, 0) + 1

    if not counts:
        return phrases.pick(phrases.STATS_EMPTY)

    medals = ["🥇", "🥈", "🥉"]
    sorted_people = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    lines = [phrases.pick(phrases.STATS_HEADER)]
    for i, (person, count) in enumerate(sorted_people):
        prefix = f"  {medals[i]} " if i < len(medals) else "  "
        lines.append(f"{prefix}{person} : {count} tâches")
    return "\n".join(lines)


def get_sunday_recap(role_assignments: dict) -> str:
    """Build a Sunday recap of the week's chore status.

    Args:
        role_assignments: dict of {role: person} for the current week.
    """
    completed = get_week_status()
    lines = [phrases.pick(phrases.SUNDAY_RECAP_HEADER)]
    for role, person in role_assignments.items():
        if is_role_complete(role, completed):
            who = _who_did_it(completed[role])
            lines.append(f"  \u2705 {role} ({person}) — fait par {who}")
        else:
            lines.append(f"  \u274c {role} ({person}) — pas fait")
    return "\n".join(lines)
