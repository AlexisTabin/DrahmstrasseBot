import pytest
import datetime
from unittest.mock import patch

from src import menage


@patch("src.menage.datetime")
def test_get_role_assignments(mock_datetime):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    # Week 41 → shift = 42
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    assignments = menage.get_role_assignments(colocataires)
    assert set(assignments.keys()) == {"CUISINE", "SDBs", "SOLs", "DÉCHETS"}
    assert set(assignments.values()) == set(colocataires)


@patch("src.menage.datetime")
def test_get_role_assignments_rotates(mock_datetime):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    # Week 41 → shift = 42
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    a1 = menage.get_role_assignments(colocataires)

    # Week 42 → shift = 43
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 16)
    a2 = menage.get_role_assignments(colocataires)

    # Roles should rotate
    assert a1["CUISINE"] != a2["CUISINE"]


@patch("src.menage.datetime")
def test_get_role_for_person(mock_datetime):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)
    assignments = menage.get_role_assignments(colocataires)

    for role, person in assignments.items():
        assert menage.get_role_for_person(colocataires, person) == role

    assert menage.get_role_for_person(colocataires, "Nobody") is None


@patch("src.menage.datetime")
def test_getRoles_changes_every_2_weeks(mock_datetime):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]

    mock_datetime.date.return_value = datetime.date(2023, 10, 9)
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)

    result_week_0 = menage.getRoles(colocataires)
    assert "CUISINE" in result_week_0
    assert "Alice" in result_week_0

    # +2 weeks
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 23)
    result_week_2 = menage.getRoles(colocataires)
    assert "Bob" in result_week_2

    # +4 weeks
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 11, 6)
    result_week_4 = menage.getRoles(colocataires)
    assert "Charlie" in result_week_4


def test_getRoles_shows_papier_carton():
    """DÉCHETS line now mentions papier + carton."""
    with patch("src.menage.datetime") as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(2023, 10, 9)
        result = menage.getRoles(["A", "B", "C", "D"])
        assert "papier + carton" in result


@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_papier_reminder(mock_assignments):
    result = menage.get_papier_reminder(["Alice", "Bob", "Charlie", "Diana"])
    assert "Diana" in result
    assert "papier" in result.lower()


@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_get_carton_reminder(mock_assignments):
    result = menage.get_carton_reminder(["Alice", "Bob", "Charlie", "Diana"])
    assert "Diana" in result
    assert "carton" in result.lower()


@patch("src.menage.get_role_assignments", return_value={
    "CUISINE": "Alice", "SDBs": "Bob", "SOLs": "Charlie", "DÉCHETS": "Diana"
})
def test_getCartonOrPapier(mock_assignments):
    result = menage.getCartonOrPapier(["Alice", "Bob", "Charlie", "Diana"])
    assert "Diana" in result
    assert "lundi" in result.lower()
    assert "mercredi" in result.lower()


def test_getCarteDeLessive_contains_url():
    result = menage.getCarteDeLessive()
    assert "https://www.lavorent.ch" in result
    assert "100 balles" in result
    assert "carte" in result.lower()


@patch("src.menage.is_even_week", return_value=True)
@patch("src.menage.getRoles", return_value="roles text")
def test_changeRoles_even_week(mock_getRoles, mock_even):
    colocataires = ["A", "B", "C", "D"]
    result = menage.changeRoles(colocataires)
    assert "Encore une semaine" in result
    assert "roles text" in result
    mock_getRoles.assert_called_once_with(colocataires)


@patch("src.menage.is_even_week", return_value=False)
@patch("src.menage.getRoles", return_value="roles text")
def test_changeRoles_odd_week(mock_getRoles, mock_even):
    colocataires = ["A", "B", "C", "D"]
    result = menage.changeRoles(colocataires)
    assert "Coucou, changement" in result
    assert "roles text" in result
    mock_getRoles.assert_called_once_with(colocataires)
