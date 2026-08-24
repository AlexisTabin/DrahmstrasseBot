import os
import logging
import datetime
import boto3
from botocore.exceptions import ClientError

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


def person_counts(sub_data: dict) -> dict:
    """Per-person press counts of a counter sub-task, as plain ints.

    Empty for an entry written before per-person counts existed (its total is
    then unattributable, see reset_subtask_counter).
    """
    counts = sub_data.get("counts") or {}
    return {person: int(n) for person, n in counts.items()}


def increment_subtask_counter(role: str, subtask: str, person: str) -> dict:
    """Increment a counter-style sub-task's per-week count.

    Returns the entry's new state, `{"count": <total>, "counts": {person: n}}`,
    read back from the write itself rather than a follow-up (eventually
    consistent) get_item.
    """
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
    # Separate call from the one above: DynamoDB rejects an expression whose
    # SET targets overlap (`...#subtask` is an ancestor of `...#subtask.#counts`),
    # and `ADD ...#counts.#person` below needs the map to already exist.
    table.update_item(
        Key={"week_key": week_key},
        UpdateExpression=(
            "SET completed.#role.subtasks.#subtask.#counts = "
            "if_not_exists(completed.#role.subtasks.#subtask.#counts, :empty_map)"
        ),
        ExpressionAttributeNames={"#role": role, "#subtask": subtask, "#counts": "counts"},
        ExpressionAttributeValues={":empty_map": {}},
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
            "completed.#role.subtasks.#subtask.#counts.#person :one, "
            "completed.#role.subtasks.#subtask.#doers :person_set"
        ),
        ExpressionAttributeNames={
            "#role": role, "#subtask": subtask, "#count": "count", "#by": "by",
            "#at": "at", "#doers": "doers", "#counts": "counts", "#person": person,
        },
        ExpressionAttributeValues={
            ":one": 1, ":person": person, ":now": now, ":person_set": {person},
        },
        ReturnValues="ALL_NEW",
    )

    new_entry = response["Attributes"]["completed"][role]["subtasks"][subtask]
    state = {"count": int(new_entry["count"]), "counts": person_counts(new_entry)}
    logger.info(
        "Incremented %s.%s to %d by %s (%dx) for %s",
        role, subtask, state["count"], person, state["counts"].get(person, 0), week_key,
    )
    return state


def reset_subtask_counter(role: str, subtask: str, person: str) -> tuple:
    """Take `person`'s own presses off a counter sub-task, leaving everyone
    else's alone. Returns (removed, new_state) where removed is how many
    presses were dropped (0 if they had none, in which case nothing is
    written) and new_state is `{"count": <total>, "counts": {...}}`.

    Presses recorded before per-person counts existed have no `counts` entry,
    so they can't be attributed and can't be reset by anyone; they only linger
    until the counter resets on Monday. When removing `person` leaves nobody
    with presses, the whole entry is rewritten as a clean `{"count": 0}` so no
    stale `by`/`doers` credit survives.

    How much to subtract can only be known by reading first, so both writes
    are guarded by a ConditionExpression on what was read and retried once:
    without it a double-tapped reset would subtract the same presses twice
    (driving the total negative, which reads as "-2x" and quietly un-completes
    the role), and the rewrite branch would clobber a "+1" that landed in the
    meantime.
    """
    table = _get_table()
    week_key = _current_week_key()
    stored, total, removed = {}, 0, 0

    for attempt in range(2):
        # Strongly consistent: an eventually consistent read here could miss
        # the caller's own press and answer "nothing to reset".
        sub_data = (
            get_week_status(week_key, consistent=True)
            .get(role, {}).get("subtasks", {}).get(subtask, {})
        )
        stored = person_counts(sub_data)
        total = int(sub_data.get("count", 0) or 0)
        removed = stored.get(person, 0)
        if removed <= 0:
            logger.info("Nothing to reset for %s on %s.%s (%s)", person, role, subtask, week_key)
            return 0, {"count": total, "counts": stored}

        remaining = {p: n for p, n in stored.items() if p != person}
        unattributed = max(0, total - sum(stored.values()))
        try:
            if not any(n >= 1 for n in remaining.values()) and unattributed == 0:
                table.update_item(
                    Key={"week_key": week_key},
                    UpdateExpression="SET completed.#role.subtasks.#subtask = :empty_counter",
                    # Nothing may have changed since the read: this branch
                    # overwrites the whole entry, so a concurrent +1 would
                    # otherwise vanish.
                    ConditionExpression="completed.#role.subtasks.#subtask.#count = :total",
                    ExpressionAttributeNames={
                        "#role": role, "#subtask": subtask, "#count": "count",
                    },
                    ExpressionAttributeValues={
                        ":empty_counter": {"count": 0, "counts": {}}, ":total": total,
                    },
                )
                logger.info(
                    "Reset %s.%s to 0 (%s was the only doer) for %s",
                    role, subtask, person, week_key,
                )
                return removed, {"count": 0, "counts": {}}

            # ADD with a negative value rather than SET, so a concurrent +1
            # press by someone else isn't clobbered; the condition covers the
            # caller's own tally, the only part this subtraction depends on.
            response = table.update_item(
                Key={"week_key": week_key},
                UpdateExpression=(
                    "REMOVE completed.#role.subtasks.#subtask.#counts.#person "
                    "ADD completed.#role.subtasks.#subtask.#count :negative "
                    "DELETE completed.#role.subtasks.#subtask.#doers :person_set"
                ),
                ConditionExpression=(
                    "completed.#role.subtasks.#subtask.#counts.#person = :removed"
                ),
                ExpressionAttributeNames={
                    "#role": role, "#subtask": subtask, "#count": "count",
                    "#counts": "counts", "#doers": "doers", "#person": person,
                },
                ExpressionAttributeValues={
                    ":negative": -removed, ":person_set": {person}, ":removed": removed,
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            logger.info(
                "Reset of %s.%s by %s raced another update (attempt %d), re-reading",
                role, subtask, person, attempt + 1,
            )
            continue

        new_entry = response["Attributes"]["completed"][role]["subtasks"][subtask]
        state = {"count": int(new_entry.get("count", 0)), "counts": person_counts(new_entry)}
        logger.info(
            "Removed %s's %d press(es) from %s.%s, %d left for %s",
            person, removed, role, subtask, state["count"], week_key,
        )
        return removed, state

    logger.warning(
        "Gave up resetting %s.%s for %s after concurrent updates", role, subtask, person,
    )
    return 0, {"count": total, "counts": stored}


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
        expected = menage.get_required_subtasks_for_role(role)
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
    expected = menage.get_required_subtasks_for_role(role)
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


def _doers_of(sub_data: dict) -> set:
    """Everyone credited for a subtask entry: the per-person `counts` map
    unioned with the `doers` set, falling back to a plain toggle's `by`.

    The union (rather than a preference) matters both ways round. Every
    increment writes both `counts` and `doers` and reset_subtask_counter
    removes the person from both, so the two never disagree about a press
    recorded by current code, and a reset still drops that person's credit.
    But an entry from before `counts` existed has doers with no counts, and
    one press after that leaves it holding both — preferring `counts` there
    would silently strip the earlier doers of their credit.
    """
    doers = {person for person, n in person_counts(sub_data).items() if n >= 1}
    doers.update(sub_data.get("doers") or set())
    if doers:
        return doers
    if "counts" in sub_data:
        # Counter entry with nothing left in counts/doers (everyone reset their
        # own presses): "by" is only ever the last presser, so falling back to
        # it here would credit someone who has taken all their presses back.
        # Keyed on "counts" existing, so the oldest counter entries (a bare
        # {count, by, at}, before either map) keep their historical credit.
        return set()
    return {sub_data["by"]} if sub_data.get("by") else set()


def _who_did_it(role_data: dict, role: str = None) -> str:
    """Extract person name(s) from either format.

    Pass `role` to leave out whoever only did an optional subtask: they get
    their own credit line via _helper_lines, and they didn't contribute to the
    role being complete.
    """
    if "by" in role_data:
        return role_data["by"]
    if "subtasks" in role_data:
        names = set()
        for subtask, sub_data in role_data["subtasks"].items():
            if role is not None and menage.is_optional_subtask(role, subtask):
                continue
            # Counter subtasks (menage.COUNTER_SUBTASKS) credit every distinct
            # incrementer; "by" alone would only be the last one.
            names.update(_doers_of(sub_data))
        return ", ".join(sorted(names)) if names else "?"
    return "?"


def get_week_status(week_key: str = None, consistent: bool = False) -> dict:
    """Get the completion status for a week. Returns the completed map (may be empty).

    `consistent` forces a strongly consistent read, for the one caller that
    computes a write from what it reads (reset_subtask_counter); the default
    eventually consistent read is fine for rendering.
    """
    table = _get_table()
    if week_key is None:
        week_key = _current_week_key()

    response = table.get_item(Key={"week_key": week_key}, ConsistentRead=consistent)
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

    Optional subtasks (menage.OPTIONAL_SUBTASKS) are left out of role_totals
    on purpose: those totals decide /leaderboard's per-role champion, and
    emptying the dishwasher every week shouldn't crown someone CUISINE
    champion over the people who actually did CUISINE. They still count
    towards person_totals and subtask_totals, i.e. participation.
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
                    optional = menage.is_optional_subtask(role, subtask)
                    for person in _doers_of(sub_data):
                        _bump(person_totals, person)
                        if not optional:
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
            if menage.is_optional_subtask(role, subtask):
                label = f"{subtask} (optionnel)"
            if menage.is_counter_subtask(role, subtask):
                label = f"{label} (participations, pas le nombre de fois)"
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


def _helper_lines(person: str, role_data: dict, role: str = None) -> list:
    """Return recap sub-lines for subtasks completed by someone other than the
    assigned person, so help from another roommate is visible in the recap.

    Pass `role` to also get a bonus line for each optional subtask that got
    done: nobody was assigned those, so every doer is credited (including the
    role's own assignee) and there's no "pas X" to report.
    """
    subtasks = role_data.get("subtasks")
    if not subtasks:
        return []
    lines = []
    for subtask, sub_data in subtasks.items():
        doers = _doers_of(sub_data)
        if role is not None and menage.is_optional_subtask(role, subtask):
            if doers:
                lines.append(
                    f"      \U0001f381 {subtask} (bonus) fait par {', '.join(sorted(doers))}"
                )
            continue
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
            who = _who_did_it(role_data, role)
            lines.append(f"  \u2705 {role} ({person}) — fait par {who}")
        else:
            lines.append(f"  \u274c {role} ({person}) — pas fait")
        lines.extend(_helper_lines(person, role_data, role))
    return "\n".join(lines)
