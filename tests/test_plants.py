import pytest
from unittest.mock import MagicMock, patch

from src import plants


@pytest.fixture(autouse=True)
def reset_table_cache():
    plants._table = None
    yield
    plants._table = None


@patch("src.plants.today_key", return_value="plant:2026-06-01")
@patch("src.plants._get_table")
def test_get_today_state_empty(mock_get_table, _key):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    assert plants.get_today_state() == {}


@patch("src.plants.today_key", return_value="plant:2026-06-01")
@patch("src.plants._get_table")
def test_get_today_state_with_data(mock_get_table, _key):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {
            "week_key": "plant:2026-06-01",
            "watering": {"state": "needs", "by": "Léa", "at": "2026-06-01T08:00:00+00:00"},
        }
    }
    mock_get_table.return_value = mock_table

    state = plants.get_today_state()
    assert state["state"] == "needs"
    assert state["by"] == "Léa"


@patch("src.plants.today_key", return_value="plant:2026-06-01")
@patch("src.plants._get_table")
def test_set_today_state_needs(mock_get_table, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = plants.set_today_state(plants.STATE_NEEDS_WATER, "Alexis")
    assert result["state"] == "needs"
    assert result["by"] == "Alexis"
    assert "at" in result
    mock_table.update_item.assert_called_once()
    call = mock_table.update_item.call_args[1]
    assert call["Key"] == {"week_key": "plant:2026-06-01"}
    assert "SET watering" in call["UpdateExpression"]


@patch("src.plants.today_key", return_value="plant:2026-06-01")
@patch("src.plants._get_table")
def test_set_today_state_ok(mock_get_table, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = plants.set_today_state(plants.STATE_OK, "Timon")
    assert result["state"] == "ok"


def test_set_today_state_invalid():
    with pytest.raises(ValueError):
        plants.set_today_state("maybe", "Alexis")


def test_today_key_format():
    key = plants.today_key()
    assert key.startswith("plant:")
    # Format YYYY-MM-DD
    date_part = key.split(":", 1)[1]
    parts = date_part.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 4
