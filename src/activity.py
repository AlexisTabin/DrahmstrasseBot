"""Time-based highlights derived from completion timestamps: streaks, gaps
and busiest days. Pure date maths, no DynamoDB — chores.py feeds it the
per-person calendar it builds while scanning the table.

A "day" here is a UTC calendar day, since that's what every timestamp is
recorded in and what the rest of the codebase already treats as today
(`chores._current_week_key`, `plants.today_key`). Zürich runs UTC+1/+2, so a
chore ticked between midnight and 02:00 local counts for the day before.
"""
import datetime

WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def day_of(stamp):
    """UTC calendar day of an ISO-8601 timestamp (or plain date), None if it
    can't be parsed: one hand-edited row shouldn't take /stats down."""
    if not stamp:
        return None
    try:
        return datetime.datetime.fromisoformat(str(stamp)).date()
    except (TypeError, ValueError):
        return None


def longest_streak(days):
    """(length, last_day) of the longest run of consecutive days."""
    ordered = sorted(set(days))
    if not ordered:
        return 0, None
    best, best_end = 1, ordered[0]
    run = 1
    for previous, current in zip(ordered, ordered[1:]):
        run = run + 1 if (current - previous).days == 1 else 1
        if run > best:
            best, best_end = run, current
    return best, best_end


def current_streak(days, today):
    """Length of the run ending today or yesterday, 0 if it's already broken.

    Yesterday still counts, otherwise every streak would read as broken until
    someone gets round to a chore today.
    """
    ordered = set(days)
    if not ordered or (today - max(ordered)).days > 1:
        return 0
    length, day = 0, max(ordered)
    while day in ordered:
        length += 1
        day -= datetime.timedelta(days=1)
    return length


def longest_gap(days):
    """(empty_days, from_day, to_day) for the longest stretch with nothing
    done between two active days. (0, None, None) below two active days."""
    ordered = sorted(set(days))
    gap, start, end = 0, None, None
    for previous, current in zip(ordered, ordered[1:]):
        empty = (current - previous).days - 1
        if empty > gap:
            gap, start, end = empty, previous, current
    return gap, start, end


def best_day(day_counts):
    """(day, count) of the busiest day; ties go to the earliest date."""
    if not day_counts:
        return None, 0
    day = min(day_counts, key=lambda d: (-day_counts[d], d))
    return day, day_counts[day]


def weekday_totals(day_counts):
    """{weekday index (Monday=0): tasks} summed over every recorded day."""
    totals = {}
    for day, count in day_counts.items():
        totals[day.weekday()] = totals.get(day.weekday(), 0) + count
    return totals


def merge_day_counts(activity):
    """Flatten {person: {day: n}} into a single {day: n} calendar."""
    merged = {}
    for day_counts in activity.values():
        for day, count in day_counts.items():
            merged[day] = merged.get(day, 0) + count
    return merged


def shared_days(calendar) -> dict:
    """{(person_a, person_b): days both were active}, pairs sorted by name so
    a duo is counted once. Only pairs with at least one shared day appear."""
    people = sorted(calendar)
    pairs = {}
    for index, first in enumerate(people):
        for second in people[index + 1:]:
            common = set(calendar[first]) & set(calendar[second])
            if common:
                pairs[(first, second)] = len(common)
    return pairs


def week_key_of(day) -> str:
    """ISO week key of a day, matching chores._current_week_key's format."""
    iso = day.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def format_day(day) -> str:
    return day.strftime("%d/%m")


def plural(count, singular, plural_form=None) -> str:
    """'1 jour' / '3 jours', so the new stat lines don't read '1 tâches'."""
    if plural_form is None:
        plural_form = singular + "s"
    return f"{count} {singular if abs(count) == 1 else plural_form}"
