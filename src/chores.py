import os
import logging
import datetime
import boto3

from src import menage
from src import phrases
from src import plants


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


def increment_subtask_counter(role: str, subtask: str, person: str) -> int:
    """Increment a counter-style sub-task's per-week count. Returns the new count."""
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
    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression=(
            "SET completed.#role.subtasks.#subtask = "
            "if_not_exists(completed.#role.subtasks.#subtask, :empty_counter)"
        ),
        ExpressionAttributeNames={"#role": role, "#subtask": subtask},
        ExpressionAttributeValues={":empty_counter": {"count": 0}},
    )
    # ADD (not "SET count = count + :one") so this is robust even if #subtask
    # was left in the pre-counter {by, at} shape by a stale toggle click:
    # ADD auto-initializes a missing numeric attribute instead of erroring.
    # "by"/"at" must be aliased — both are DynamoDB reserved words when used
    # as a raw path segment (only safe as plain dict keys inside a value).
    response = table.update_item(
        Key={"week_key": week_key},
        UpdateExpression=(
            "SET completed.#role.subtasks.#subtask.#by = :person, "
            "completed.#role.subtasks.#subtask.#at = :now "
            "ADD completed.#role.subtasks.#subtask.#count :one, "
            "completed.#role.subtasks.#subtask.#doers :person_set"
        ),
        ExpressionAttributeNames={
            "#role": role, "#subtask": subtask,
            "#count": "count", "#by": "by", "#at": "at", "#doers": "doers",
        },
        ExpressionAttributeValues={
            ":one": 1, ":person": person, ":now": now, ":person_set": {person},
        },
        ReturnValues="UPDATED_NEW",
    )

    new_count = int(response["Attributes"]["completed"][role]["subtasks"][subtask]["count"])
    logger.info("Incremented %s.%s to %d by %s for %s", role, subtask, new_count, person, week_key)
    return new_count


def reset_subtask_counter(role: str, subtask: str) -> None:
    """Reset a counter-style sub-task's count back to 0 for everyone this
    week. No confirmation needed: an accidental reset is trivially undone by
    re-pressing +1 the same number of times."""
    table = _get_table()
    week_key = _current_week_key()

    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression="SET completed.#role.subtasks.#subtask = :empty_counter",
        ExpressionAttributeNames={"#role": role, "#subtask": subtask},
        ExpressionAttributeValues={":empty_counter": {"count": 0}},
    )
    logger.info("Reset %s.%s counter to 0 for %s", role, subtask, week_key)


def is_subtask_satisfied(sub_data: dict) -> bool:
    """Whether a subtask entry counts as done: any entry for a toggle subtask,
    count >= 1 for a counter subtask (see menage.COUNTER_SUBTASKS)."""
    if "count" in sub_data:
        return sub_data["count"] >= 1
    return True


def is_role_complete(role: str, completed_map: dict) -> bool:
    """Check if a role is fully completed, handling both old and new formats."""
    if role not in completed_map:
        return False

    role_data = completed_map[role]

    # Old format: {by, at}
    if "by" in role_data:
        return True

    # New format: {subtasks: {name: {by, at}, ...}}
    if "subtasks" in role_data:
        expected = menage.get_subtasks_for_role(role)
        if expected is None:
            return False
        completed_subtasks = role_data["subtasks"]
        return all(
            s in completed_subtasks and is_subtask_satisfied(completed_subtasks[s])
            for s in expected
        )

    return False


def _pending_detail(role: str, completed: dict) -> str:
    """Return detail string for sub-task roles with missing items."""
    expected = menage.get_subtasks_for_role(role)
    if expected is None:
        return ""

    role_data = completed.get(role, {})

    # Old format: {by, at} — no subtask detail to show
    if "by" in role_data:
        return ""

    completed_subtasks = role_data.get("subtasks", {})
    missing = [
        s for s in expected
        if s not in completed_subtasks or not is_subtask_satisfied(completed_subtasks[s])
    ]
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
            # Counter subtasks (menage.COUNTER_SUBTASKS) track every distinct
            # incrementer in "doers"; "by" alone would only be the last one.
            if "doers" in sub_data:
                names.update(sub_data["doers"])
            elif "by" in sub_data:
                names.add(sub_data["by"])
        return ", ".join(sorted(names)) if names else "?"
    return "?"


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


def _bump(counts: dict, key) -> None:
    counts[key] = counts.get(key, 0) + 1


def _grouped_by_score(totals: dict) -> list:
    """Group people by score, descending, ties combined into one entry so a
    medal/rank never implies a false ordering between people who are tied.
    Returns [(score, [people sorted alphabetically]), ...].
    """
    scores = sorted(set(totals.values()), reverse=True)
    return [(score, sorted(p for p, c in totals.items() if c == score)) for score in scores]


def _aggregate_completions() -> dict:
    """Scan every row once and bucket chore completions by person, role, and
    (role, subtask), plus a cendrier trivia count. Every subtask completion
    counts on its own: unlike the older role-only counting still used
    elsewhere, a role doesn't need to be fully finished for its subtask
    credits to show up here.

    Old-format {by, at} role entries only contribute to the person/role
    totals: there's no subtask breakdown to attribute for them.
    """
    table = _get_table()
    items = table.scan().get("Items", [])

    person_totals: dict[str, int] = {}
    role_totals: dict[str, dict[str, int]] = {}
    subtask_totals: dict[tuple, dict[str, int]] = {}
    weeks_tracked = 0
    cendrier_weeks = 0

    for item in items:
        if "cendrier" in item:
            cendrier_weeks += 1
            continue
        completed = item.get("completed")
        if completed is None:
            continue
        weeks_tracked += 1
        for role, role_data in completed.items():
            if "by" in role_data:
                person = role_data["by"]
                _bump(person_totals, person)
                _bump(role_totals.setdefault(role, {}), person)
            elif "subtasks" in role_data:
                for subtask, sub_data in role_data["subtasks"].items():
                    doers = sub_data.get("doers")
                    if doers is None:
                        doers = {sub_data["by"]} if sub_data.get("by") else set()
                    for person in doers:
                        _bump(person_totals, person)
                        _bump(role_totals.setdefault(role, {}), person)
                        _bump(subtask_totals.setdefault((role, subtask), {}), person)

    return {
        "person_totals": person_totals,
        "role_totals": role_totals,
        "subtask_totals": subtask_totals,
        "weeks_tracked": weeks_tracked,
        "cendrier_weeks": cendrier_weeks,
        # Folded into this same scan so get_stats/get_leaderboard don't pay
        # for a second full table.scan() via plants.get_watering_totals().
        "plant_totals": plants.compute_watering_totals(items),
    }


def get_stats() -> str:
    """Exhaustive, dev-chat-only breakdown: every person's total, a per-role
    and per-subtask breakdown, averages, and the most/least active people.
    See get_leaderboard() for the positive-only, public equivalent.
    """
    agg = _aggregate_completions()
    person_totals = agg["person_totals"]
    plant_totals = agg["plant_totals"]

    if not person_totals and not plant_totals and not agg["cendrier_weeks"]:
        return phrases.pick(phrases.STATS_EMPTY)

    lines = [phrases.pick(phrases.STATS_HEADER)]

    if person_totals:
        grouped = _grouped_by_score(person_totals)
        medals = ["🥇", "🥈", "🥉"]
        lines.append("")
        lines.append("🏆 Classement général")
        for i, (count, people) in enumerate(grouped):
            prefix = f"  {medals[i]} " if i < len(medals) else "     "
            lines.append(f"{prefix}{', '.join(people)} : {count} tâches")

        total = sum(person_totals.values())
        avg = total / len(person_totals)
        lines.append("")
        lines.append(
            f"📈 {agg['weeks_tracked']} semaine(s) suivie(s) · "
            f"moyenne {avg:.1f} tâches/personne"
        )
        top_count, top_people = grouped[0]
        bottom_count, bottom_people = grouped[-1]
        lines.append(f"🔥 Plus actif·ve : {', '.join(top_people)}")
        if bottom_count != top_count:
            lines.append(f"🥶 Moins actif·ve : {', '.join(bottom_people)}")

    for role in menage.ROLES:
        role_counts = agg["role_totals"].get(role)
        if not role_counts:
            continue
        lines.append("")
        lines.append(f"{menage.ROLE_EMOJIS.get(role, '')} {role}")
        for person, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {person} : {count}")

    if agg["subtask_totals"]:
        lines.append("")
        lines.append("🔍 Détail par tâche")
        sorted_subtasks = sorted(
            agg["subtask_totals"].items(), key=lambda x: (x[0][0], x[0][1].lower())
        )
        for (role, subtask), counts in sorted_subtasks:
            label = subtask
            if menage.is_counter_subtask(role, subtask):
                label = f"{subtask} (participations, pas le nombre de fois)"
            parts = ", ".join(
                f"{person} {count}"
                for person, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
            )
            lines.append(f"  {label} : {parts}")

    if plant_totals:
        lines.append("")
        lines.append("🌱 Arrosage des plantes")
        for person, count in sorted(plant_totals.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {person} : {count}")

    if agg["cendrier_weeks"]:
        lines.append("")
        lines.append(f"🚬 Cendrier sorti {agg['cendrier_weeks']} fois (toujours par Maël)")

    return "\n".join(lines)


def get_leaderboard() -> str:
    """Positive-only, all-time highlights for everyone to see: the top
    scorer(s), a champion per role, and the plant-watering MVP. No bottom
    rankings: see get_stats() for the exhaustive, dev-chat-only breakdown.
    """
    agg = _aggregate_completions()
    person_totals = agg["person_totals"]
    plant_totals = agg["plant_totals"]

    if not person_totals and not plant_totals:
        return phrases.pick(phrases.LEADERBOARD_EMPTY)

    lines = [phrases.pick(phrases.LEADERBOARD_HEADER)]

    if person_totals:
        grouped = _grouped_by_score(person_totals)[:3]
        medals = ["🥇", "🥈", "🥉"]
        lines.append("")
        lines.append("🏆 Classement général")
        for i, (count, people) in enumerate(grouped):
            lines.append(f"  {medals[i]} {', '.join(people)} : {count} tâches")

    if agg["role_totals"]:
        lines.append("")
        for role in menage.ROLES:
            role_counts = agg["role_totals"].get(role)
            if not role_counts:
                continue
            top_count, champions = _grouped_by_score(role_counts)[0]
            lines.append(
                f"{menage.ROLE_EMOJIS.get(role, '')} {role} : {', '.join(champions)} "
                f"({top_count} fois)"
            )

    if plant_totals:
        top_count, friends = _grouped_by_score(plant_totals)[0]
        lines.append("")
        lines.append(f"🌱 Best Plant Friend : {', '.join(friends)} ({top_count} arrosages)")

    return "\n".join(lines)


def _helper_lines(person: str, role_data: dict) -> list:
    """Return recap sub-lines for subtasks completed by someone other than the
    assigned person, so help from another roommate is visible in the recap."""
    subtasks = role_data.get("subtasks")
    if not subtasks:
        return []
    lines = []
    for subtask, sub_data in subtasks.items():
        doers = sub_data.get("doers")
        if doers is None:
            doers = {sub_data["by"]} if sub_data.get("by") else set()
        others = sorted(doer for doer in doers if doer != person)
        if others:
            lines.append(f"      \U0001f91d {subtask} fait par {', '.join(others)} (pas {person})")
    return lines


def get_sunday_recap(role_assignments: dict) -> str:
    """Build a Sunday recap of the week's chore status.

    Args:
        role_assignments: dict of {role: person} for the current week.
    """
    completed = get_week_status()
    lines = [phrases.pick(phrases.SUNDAY_RECAP_HEADER)]
    for role, person in role_assignments.items():
        role_data = completed.get(role, {})
        if is_role_complete(role, completed):
            who = _who_did_it(role_data)
            lines.append(f"  \u2705 {role} ({person}) — fait par {who}")
        else:
            lines.append(f"  \u274c {role} ({person}) — pas fait")
        lines.extend(_helper_lines(person, role_data))
    return "\n".join(lines)
