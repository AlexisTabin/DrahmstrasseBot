import pytest
import datetime
from unittest.mock import patch

from src import menage


@patch("src.menage.datetime")
def test_getRoles_changes_every_2_weeks(mock_datetime):
    colocataires = ["Alice", "Bob", "Charlie", "Diana"]

    # Mock the initial reference date
    mock_datetime.date.return_value = datetime.date(2023, 10, 9)
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 9)

    # Week 0 (no rotation)
    result_week_0 = menage.getRoles(colocataires)
    assert "CUISINE" in result_week_0
    assert "Alice" in result_week_0  # Starts with Alice

    # +2 weeks → rotation by 1
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 23)
    result_week_2 = menage.getRoles(colocataires)
    assert "Bob" in result_week_2  # Rotated by 1

    # +4 weeks → rotation by 2
    mock_datetime.datetime.now.return_value = datetime.datetime(2023, 11, 6)
    result_week_4 = menage.getRoles(colocataires)
    assert "Charlie" in result_week_4  # Rotated by 2


@patch("src.menage.is_even_week", return_value=True)
def test_getCartonOrPapier_even(mock_even):
    result = menage.getCartonOrPapier()
    assert "papier" in result.lower()
    mock_even.assert_called_once()


@patch("src.menage.is_even_week", return_value=False)
def test_getCartonOrPapier_odd(mock_even):
    result = menage.getCartonOrPapier()
    assert "carton" in result.lower()
    mock_even.assert_called_once()


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

