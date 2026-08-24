import datetime

from src import activity


def day(*args):
    """Shorthand for a 2026-05-XX date."""
    return datetime.date(2026, 5, *args)


# --- day_of ---


def test_day_of_parses_a_stored_timestamp():
    assert activity.day_of("2026-05-03T19:42:11+00:00") == day(3)


def test_day_of_parses_a_plain_date():
    """Counter `days` sets store bare dates, not timestamps."""
    assert activity.day_of("2026-05-03") == day(3)


def test_day_of_returns_none_for_junk():
    """One hand-edited row shouldn't take the whole /stats command down."""
    assert activity.day_of("pas une date") is None
    assert activity.day_of(None) is None
    assert activity.day_of("") is None


# --- longest_streak ---


def test_longest_streak_counts_consecutive_days():
    days = [day(1), day(2), day(3), day(7)]
    assert activity.longest_streak(days) == (3, day(3))


def test_longest_streak_keeps_the_first_of_two_equal_runs():
    days = [day(1), day(2), day(5), day(6)]
    assert activity.longest_streak(days) == (2, day(2))


def test_longest_streak_ignores_duplicate_days():
    assert activity.longest_streak([day(1), day(1), day(2)]) == (2, day(2))


def test_longest_streak_of_a_single_day():
    assert activity.longest_streak([day(4)]) == (1, day(4))


def test_longest_streak_empty():
    assert activity.longest_streak([]) == (0, None)


# --- current_streak ---


def test_current_streak_counts_back_from_today():
    days = [day(1), day(8), day(9), day(10)]
    assert activity.current_streak(days, today=day(10)) == 3


def test_current_streak_still_counts_when_the_last_day_was_yesterday():
    """Otherwise every streak would read as broken until someone gets round
    to a chore today."""
    assert activity.current_streak([day(9), day(10)], today=day(11)) == 2


def test_current_streak_is_zero_once_a_day_was_missed():
    assert activity.current_streak([day(9), day(10)], today=day(12)) == 0


def test_current_streak_empty():
    assert activity.current_streak([], today=day(12)) == 0


# --- longest_gap ---


def test_longest_gap_counts_the_empty_days_between_two_active_ones():
    days = [day(1), day(2), day(10), day(11)]
    assert activity.longest_gap(days) == (7, day(2), day(10))


def test_longest_gap_of_consecutive_days_is_zero():
    assert activity.longest_gap([day(1), day(2), day(3)]) == (0, None, None)


def test_longest_gap_needs_two_days():
    assert activity.longest_gap([day(1)]) == (0, None, None)
    assert activity.longest_gap([]) == (0, None, None)


# --- best_day / weekday_totals / merge_day_counts ---


def test_best_day_picks_the_busiest():
    assert activity.best_day({day(1): 2, day(2): 5, day(3): 1}) == (day(2), 5)


def test_best_day_breaks_ties_on_the_earliest_date():
    assert activity.best_day({day(4): 3, day(2): 3}) == (day(2), 3)


def test_best_day_empty():
    assert activity.best_day({}) == (None, 0)


def test_weekday_totals_sums_by_day_of_week():
    # 2026-05-04 is a Monday, 2026-05-11 the Monday after, 2026-05-05 a Tuesday.
    totals = activity.weekday_totals({day(4): 2, day(11): 3, day(5): 1})
    assert totals == {0: 5, 1: 1}


def test_merge_day_counts_sums_across_people():
    calendar = {"Timon": {day(1): 2, day(2): 1}, "Léa": {day(1): 3}}
    assert activity.merge_day_counts(calendar) == {day(1): 5, day(2): 1}


# --- shared_days ---


def test_shared_days_counts_days_two_people_were_both_active():
    calendar = {
        "Timon": {day(1): 1, day(2): 1, day(3): 1},
        "Léa": {day(2): 1, day(3): 1},
        "Maël": {day(9): 1},
    }
    pairs = activity.shared_days(calendar)
    assert pairs == {("Léa", "Timon"): 2}  # Maël shares no day with anyone


def test_shared_days_keys_are_name_sorted_so_a_duo_is_counted_once():
    calendar = {"Timon": {day(1): 1}, "Alexis": {day(1): 1}}
    assert list(activity.shared_days(calendar)) == [("Alexis", "Timon")]


def test_shared_days_empty():
    assert activity.shared_days({}) == {}


# --- formatting helpers ---


def test_week_key_of_matches_the_chores_week_key_format():
    assert activity.week_key_of(datetime.date(2026, 4, 2)) == "2026-W14"


def test_format_day():
    assert activity.format_day(day(3)) == "03/05"


def test_plural():
    assert activity.plural(1, "jour") == "1 jour"
    assert activity.plural(3, "jour") == "3 jours"
    assert activity.plural(1, "jour actif", "jours actifs") == "1 jour actif"
    assert activity.plural(0, "tâche") == "0 tâches"
