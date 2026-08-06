import pytest
import datetime
from unittest.mock import patch

from src import menage


@patch("src.menage._should_keep_same_roles", return_value=False)
@patch("src.menage.datetime")
def test_get_role_assignments(mock_datetime, mock_chaos):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    # Week 41 → shift = 42
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    assignments = menage.get_role_assignments(colocataires)
    assert set(assignments.keys()) == {"CUISINE", "SDBs", "SOLs", "DÉCHETS"}
    assert set(assignments.values()) == set(colocataires)


@patch("src.menage._should_keep_same_roles", return_value=False)
@patch("src.menage.datetime")
def test_get_role_assignments_rotates(mock_datetime, mock_chaos):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    # Week 41 → shift = 42
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    a1 = menage.get_role_assignments(colocataires)

    # Week 42 → shift = 43
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 16)
    a2 = menage.get_role_assignments(colocataires)

    # Roles should rotate
    assert a1["CUISINE"] != a2["CUISINE"]


@patch("src.menage._should_keep_same_roles", return_value=False)
@patch("src.menage.datetime")
def test_get_role_for_person(mock_datetime, mock_chaos):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    assignments = menage.get_role_assignments(colocataires)

    for role, person in assignments.items():
        assert menage.get_role_for_person(colocataires, person) == role

    assert menage.get_role_for_person(colocataires, "Nobody") is None


def test_getRoles_has_dechets():
    """DÉCHETS line is present."""
    with patch("src.menage._should_keep_same_roles", return_value=False), \
         patch("src.menage.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(2023, 10, 9)
        result = menage.getRoles(["A", "B", "C", "D"])
        assert "DÉCHET" in result


@patch("src.menage._should_keep_same_roles", return_value=False)
@patch("src.menage.datetime")
def test_getRoles_normal_week_uses_new_roles_phrase(mock_datetime, mock_chaos):
    from src.phrases import MONDAY_NEW_ROLES
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    result = menage.getRoles(["A", "B", "C", "D"])
    assert any(p in result for p in MONDAY_NEW_ROLES)


@patch("src.menage._should_keep_same_roles", return_value=True)
@patch("src.menage.datetime")
def test_getRoles_chaos_week_uses_same_roles_phrase(mock_datetime, mock_chaos):
    from src.phrases import MONDAY_SAME_ROLES
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    result = menage.getRoles(["A", "B", "C", "D"])
    assert any(p in result for p in MONDAY_SAME_ROLES)


@patch("src.menage._should_keep_same_roles", return_value=True)
@patch("src.menage.datetime")
def test_get_role_assignments_chaos_matches_previous_week(mock_datetime, mock_chaos):
    """On a chaos week the shift is -1, giving the same assignment as a normal previous week."""
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 16)  # Week 42
    chaos = menage.get_role_assignments(colocataires)

    # Normal week 41 assignments
    mock_chaos.return_value = False
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)  # Week 41
    normal_previous = menage.get_role_assignments(colocataires)

    assert chaos == normal_previous


def test_should_keep_same_roles_is_deterministic_per_week():
    """Calling twice in the same week yields the same result — required so reminders/recap agree with /roles."""
    with patch("src.menage.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(2023, 10, 9)
        first = menage._should_keep_same_roles()
        second = menage._should_keep_same_roles()
        assert first == second


@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_papier_reminder(mock_assignments):
    result = menage.get_papier_reminder(["Alice", "Bob", "Charlie", "Diana"])
    assert "Diana" in result
    assert "papier" in result.lower()
    assert "lundi" in result.lower()


@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_carton_reminder(mock_assignments):
    result = menage.get_carton_reminder(["Alice", "Bob", "Charlie", "Diana"])
    assert "Diana" in result
    assert "carton" in result.lower()
    assert "mercredi" in result.lower()


def test_getCarteDeLessive_contains_url():
    result = menage.getCarteDeLessive()
    assert "https://www.lavorent.ch" in result
    assert "100 balles" in result
    assert "carte" in result.lower()


# --- Sub-task definitions tests ---


def test_role_subtasks_keys_match_roles():
    from src.menage import ROLE_SUBTASKS, ROLES
    assert set(ROLE_SUBTASKS.keys()) == set(ROLES)


def test_cuisine_subtasks():
    from src.menage import ROLE_SUBTASKS
    assert ROLE_SUBTASKS["CUISINE"] == ["frigo", "plan de travail", "rangement", "balcon"]


def test_sdbs_subtasks():
    from src.menage import ROLE_SUBTASKS
    assert ROLE_SUBTASKS["SDBs"] == [
        "petit WC", "grand WC", "lavabo", "baignoire", "Vider les petites poubelles",
    ]


def test_sols_subtasks():
    from src.menage import ROLE_SUBTASKS
    assert ROLE_SUBTASKS["SOLs"] == ["aspirateur", "panosse"]


def test_dechets_base_subtasks_exclude_papier():
    from src.menage import ROLE_SUBTASKS
    assert "papier" not in ROLE_SUBTASKS["DÉCHETS"]
    assert "poubelle" in ROLE_SUBTASKS["DÉCHETS"]


@patch("src.menage.is_even_week", return_value=True)
def test_get_subtasks_dechets_even_week_includes_papier(mock_even):
    from src.menage import get_subtasks_for_role
    result = get_subtasks_for_role("DÉCHETS")
    assert "papier" in result
    assert "poubelle" in result
    assert len(result) == 6


@patch("src.menage.is_even_week", return_value=False)
def test_get_subtasks_dechets_odd_week_excludes_papier(mock_even):
    from src.menage import get_subtasks_for_role
    result = get_subtasks_for_role("DÉCHETS")
    assert "papier" not in result
    assert "poubelle" in result
    assert len(result) == 5


def test_get_subtasks_cuisine():
    from src.menage import get_subtasks_for_role
    result = get_subtasks_for_role("CUISINE")
    assert result == ["frigo", "plan de travail", "rangement", "balcon"]


def test_get_subtasks_sdbs():
    from src.menage import get_subtasks_for_role
    result = get_subtasks_for_role("SDBs")
    assert result == [
        "petit WC", "grand WC", "lavabo", "baignoire", "Vider les petites poubelles",
    ]


def test_get_subtasks_unknown_role_returns_none():
    from src.menage import get_subtasks_for_role
    assert get_subtasks_for_role("UNKNOWN") is None


def test_get_subtasks_sols():
    from src.menage import get_subtasks_for_role
    result = get_subtasks_for_role("SOLs")
    assert result == ["aspirateur", "panosse"]


def test_get_subtasks_returns_copy():
    """Modifying the returned list should not affect the original."""
    from src.menage import get_subtasks_for_role, ROLE_SUBTASKS
    result = get_subtasks_for_role("SOLs")
    result.append("extra")
    assert "extra" not in ROLE_SUBTASKS["SOLs"]


# --- SUBTASK_COMMANDS tests ---


def test_subtask_commands_map_to_known_roles_and_subtasks():
    from src.menage import SUBTASK_COMMANDS, ROLE_SUBTASKS
    for cmd, (role, subtask) in SUBTASK_COMMANDS.items():
        assert role in ROLE_SUBTASKS, f"{cmd} maps to unknown role {role}"
        assert subtask in ROLE_SUBTASKS[role], f"{cmd} maps to unknown subtask {subtask}"


def test_subtask_commands_cover_every_subtask_except_papier_and_carton():
    from src.menage import SUBTASK_COMMANDS, ROLE_SUBTASKS
    mapped_subtasks = {(role, subtask) for role, subtask in SUBTASK_COMMANDS.values()}
    for role, subtasks in ROLE_SUBTASKS.items():
        for subtask in subtasks:
            if subtask == "carton":
                continue  # /carton already exists with its own reminder text
            assert (role, subtask) in mapped_subtasks, f"{role}.{subtask} has no command"


def test_subtask_commands_exclude_papier():
    """papier already has its own dedicated /papier command."""
    from src.menage import SUBTASK_COMMANDS
    assert "papier" not in SUBTASK_COMMANDS


def test_subtask_commands_are_valid_telegram_command_names():
    """Telegram commands must be lowercase alphanumeric/underscore, <=32 chars."""
    import re
    from src.menage import SUBTASK_COMMANDS
    for cmd in SUBTASK_COMMANDS:
        assert re.fullmatch(r"[a-z0-9_]{1,32}", cmd), f"invalid command name: {cmd}"


# --- Holiday redistribution ---

ALL_COLOCATAIRES = ["Timon", "Maël", "Léa", "Alexis"]


@patch("src.menage.datetime")
def test_get_holiday_redistribution_excludes_absent_person(mock_datetime):
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    result = menage.get_holiday_redistribution("CUISINE", "Timon", ALL_COLOCATAIRES)
    assert "Timon" not in result.values()
    assert set(result.keys()) == set(menage.get_subtasks_for_role("CUISINE"))


@patch("src.menage.datetime")
def test_get_holiday_redistribution_deterministic_same_week(mock_datetime):
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    a = menage.get_holiday_redistribution("CUISINE", "Timon", ALL_COLOCATAIRES)
    b = menage.get_holiday_redistribution("CUISINE", "Timon", ALL_COLOCATAIRES)
    assert a == b


@patch("src.menage.datetime")
def test_get_holiday_redistribution_independent_of_input_order(mock_datetime):
    """chores.py derives its colocataires list from role_assignments.values()
    (ordered by role), while drahmbot.py uses its own fixed list — same
    people, different order. The result must agree regardless, or /recap and
    /vacances would disagree about who's actually doing what."""
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    reordered = list(reversed(ALL_COLOCATAIRES))
    a = menage.get_holiday_redistribution("CUISINE", "Timon", ALL_COLOCATAIRES)
    b = menage.get_holiday_redistribution("CUISINE", "Timon", reordered)
    assert a == b


@patch("src.menage.datetime")
def test_get_holiday_redistribution_is_balanced(mock_datetime):
    """5 SDBs subtasks over 3 remaining people should split as evenly as possible."""
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    result = menage.get_holiday_redistribution("SDBs", "Maël", ALL_COLOCATAIRES)
    counts = {}
    for assignee in result.values():
        counts[assignee] = counts.get(assignee, 0) + 1
    assert set(counts.keys()) == {"Timon", "Léa", "Alexis"}
    assert max(counts.values()) - min(counts.values()) <= 1


def test_get_holiday_redistribution_unknown_role_returns_empty():
    assert menage.get_holiday_redistribution("UNKNOWN", "Timon", ALL_COLOCATAIRES) == {}


def test_get_holiday_redistribution_no_one_else_returns_empty():
    assert menage.get_holiday_redistribution("CUISINE", "Timon", ["Timon"]) == {}


@patch("src.menage.datetime")
def test_get_holiday_redistribution_excludes_other_holiday_people(mock_datetime):
    """Léa being on holiday too shouldn't make her eligible for Timon's
    redistributed subtasks."""
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    result = menage.get_holiday_redistribution(
        "CUISINE", "Timon", ALL_COLOCATAIRES, holiday_people={"Timon", "Léa"},
    )
    assert "Léa" not in result.values()
    assert "Timon" not in result.values()
    assert set(result.values()) <= {"Maël", "Alexis"}


@patch("src.menage.datetime")
def test_get_holiday_redistribution_everyone_else_on_holiday_returns_empty(mock_datetime):
    """If nobody's eligible, nothing gets redistributed — no task needs doing."""
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    result = menage.get_holiday_redistribution(
        "CUISINE", "Timon", ALL_COLOCATAIRES,
        holiday_people={"Timon", "Maël", "Léa", "Alexis"},
    )
    assert result == {}


# --- get_effective_assignee ---


def test_get_effective_assignee_returns_assigned_when_not_on_holiday():
    result = menage.get_effective_assignee(
        "CUISINE", "frigo", "Timon", set(), ALL_COLOCATAIRES,
    )
    assert result == "Timon"


@patch("src.menage.datetime")
def test_get_effective_assignee_returns_redistributed_when_on_holiday(mock_datetime):
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    redistribution = menage.get_holiday_redistribution("CUISINE", "Timon", ALL_COLOCATAIRES)
    result = menage.get_effective_assignee(
        "CUISINE", "frigo", "Timon", {"Timon"}, ALL_COLOCATAIRES,
    )
    assert result == redistribution["frigo"]
    assert result != "Timon"


def test_get_effective_assignee_ignores_unrelated_holiday_people():
    """Someone else being on holiday shouldn't affect this role's assignee."""
    result = menage.get_effective_assignee(
        "CUISINE", "frigo", "Timon", {"Léa"}, ALL_COLOCATAIRES,
    )
    assert result == "Timon"


def test_get_effective_assignee_falls_back_to_assigned_when_everyone_away():
    """If literally everyone is on holiday, there's no one to redistribute to
    — the assigned person stays the (nominal, unreachable) assignee rather
    than the call crashing or picking another holidaying person."""
    result = menage.get_effective_assignee(
        "CUISINE", "frigo", "Timon",
        {"Timon", "Maël", "Léa", "Alexis"}, ALL_COLOCATAIRES,
    )
    assert result == "Timon"


# --- get_effective_subtasks_for_person (drives /done) ---


SAMPLE_ROLE_ASSIGNMENTS = {
    "CUISINE": "Timon", "SDBs": "Maël", "SOLs": "Léa", "DÉCHETS": "Alexis",
}


def test_get_effective_subtasks_for_person_no_holiday_is_just_own_role():
    pairs = menage.get_effective_subtasks_for_person(
        "Timon", SAMPLE_ROLE_ASSIGNMENTS, set(), ALL_COLOCATAIRES,
    )
    assert set(pairs) == {
        ("CUISINE", "frigo"),
        ("CUISINE", "plan de travail"),
        ("CUISINE", "rangement"),
        ("CUISINE", "balcon"),
    }


@patch("src.menage.datetime")
def test_get_effective_subtasks_for_person_gains_redistributed_subtask(mock_datetime):
    """The real bug being fixed: a helper who inherited a subtask from a
    holidaying roommate can now find it via /done, not just via /frigo."""
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    holiday_people = {"Timon"}
    redistribution = menage.get_holiday_redistribution(
        "CUISINE", "Timon", ALL_COLOCATAIRES, holiday_people,
    )
    helper = redistribution["frigo"]

    pairs = menage.get_effective_subtasks_for_person(
        helper, SAMPLE_ROLE_ASSIGNMENTS, holiday_people, ALL_COLOCATAIRES,
    )
    assert ("CUISINE", "frigo") in pairs


@patch("src.menage.datetime")
def test_get_effective_subtasks_for_person_loses_redistributed_subtask(mock_datetime):
    """Timon, on holiday, no longer sees the CUISINE subtasks that got
    redistributed away — they aren't his to do this week."""
    mock_datetime.datetime.now.return_value = datetime.datetime(2026, 4, 1)
    holiday_people = {"Timon"}
    pairs = menage.get_effective_subtasks_for_person(
        "Timon", SAMPLE_ROLE_ASSIGNMENTS, holiday_people, ALL_COLOCATAIRES,
    )
    assert pairs == []


# --- papier/carton reminders respect holiday redistribution ---


@patch("src.menage.get_holiday_redistribution", return_value={"papier": "Alice"})
@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_papier_reminder_respects_holiday(mock_assignments, mock_redistribution):
    result = menage.get_papier_reminder(
        ["Alice", "Bob", "Charlie", "Diana"], holiday_people={"Diana"},
    )
    assert "Alice" in result
    assert "Diana" not in result


@patch("src.menage.get_holiday_redistribution", return_value={"carton": "Bob"})
@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_carton_reminder_respects_holiday(mock_assignments, mock_redistribution):
    result = menage.get_carton_reminder(
        ["Alice", "Bob", "Charlie", "Diana"], holiday_people={"Diana"},
    )
    assert "Bob" in result
    assert "Diana" not in result


@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_papier_reminder_no_holiday_people_arg_keeps_old_behavior(mock_assignments):
    """Callers that don't pass holiday_people (e.g. old call sites) still work."""
    result = menage.get_papier_reminder(["Alice", "Bob", "Charlie", "Diana"])
    assert "Diana" in result
