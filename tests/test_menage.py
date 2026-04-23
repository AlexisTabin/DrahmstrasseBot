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
    assert ROLE_SUBTASKS["CUISINE"] == ["frigo", "plan de travail", "rangement"]


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
    assert result == ["frigo", "plan de travail", "rangement"]


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
