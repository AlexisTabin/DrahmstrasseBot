import datetime

import pytest
from unittest.mock import MagicMock, patch

from src import cendrier


@pytest.fixture(autouse=True)
def reset_table_cache():
    """Reset the cached table between tests."""
    cendrier._table = None
    yield
    cendrier._table = None


@patch("src.cendrier._current_week_key", return_value="cendrier:2026-W14")
@patch("src.cendrier._get_table")
def test_get_week_state_empty(mock_get_table, _key):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    assert cendrier.get_week_state() == {}


@patch("src.cendrier._current_week_key", return_value="cendrier:2026-W14")
@patch("src.cendrier._get_table")
def test_get_week_state_with_data(mock_get_table, _key):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {
            "week_key": "cendrier:2026-W14",
            "cendrier": {"by": "Maël", "at": "2026-04-01T10:00:00+00:00"},
        }
    }
    mock_get_table.return_value = mock_table

    state = cendrier.get_week_state()
    assert state["by"] == "Maël"


@patch("src.cendrier._current_week_key", return_value="cendrier:2026-W14")
@patch("src.cendrier.get_week_state", return_value={})
@patch("src.cendrier._get_table")
def test_toggle_week_state_sets_it(mock_get_table, _state, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = cendrier.toggle_week_state("Maël")
    assert result["by"] == "Maël"
    assert "at" in result
    call = mock_table.update_item.call_args[1]
    assert call["Key"] == {"week_key": "cendrier:2026-W14"}
    assert "SET cendrier" in call["UpdateExpression"]


@patch("src.cendrier._current_week_key", return_value="cendrier:2026-W14")
@patch("src.cendrier.get_week_state", return_value={"by": "Maël", "at": "..."})
@patch("src.cendrier._get_table")
def test_toggle_week_state_clears_when_set(mock_get_table, _state, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = cendrier.toggle_week_state("Maël")
    assert result == {}
    call = mock_table.update_item.call_args[1]
    assert "REMOVE cendrier" in call["UpdateExpression"]


@patch("src.cendrier.datetime")
def test_current_week_key_format(mock_dt):
    mock_dt.date.today.return_value = datetime.date(2026, 4, 1)
    key = cendrier._current_week_key()
    iso = datetime.date(2026, 4, 1).isocalendar()
    assert key == f"cendrier:{iso[0]}-W{iso[1]:02d}"


@patch("src.cendrier.boto3")
def test_get_table_creates_and_caches(mock_boto3):
    table = cendrier._get_table()

    mock_boto3.resource.assert_called_once_with("dynamodb")
    mock_boto3.resource.return_value.Table.assert_called_once_with(
        "drahmstrassebot-chores"
    )
    assert table is mock_boto3.resource.return_value.Table.return_value

    # A second call must reuse the cached table, not recreate it.
    table2 = cendrier._get_table()
    assert table2 is table
    assert mock_boto3.resource.call_count == 1
