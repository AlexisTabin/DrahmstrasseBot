import datetime

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
@patch("src.plants.get_today_state", return_value={})
@patch("src.plants._get_table")
def test_toggle_today_state_sets_watered(mock_get_table, _state, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = plants.toggle_today_state("Alexis")
    assert result["state"] == "watered"
    assert result["by"] == "Alexis"
    assert "at" in result
    mock_table.update_item.assert_called_once()
    call = mock_table.update_item.call_args[1]
    assert call["Key"] == {"week_key": "plant:2026-06-01"}
    assert "SET watering" in call["UpdateExpression"]


@patch("src.plants.today_key", return_value="plant:2026-06-01")
@patch("src.plants.get_today_state",
       return_value={"state": "watered", "by": "Léa", "at": "..."})
@patch("src.plants._get_table")
def test_toggle_today_state_clears_when_watered(mock_get_table, _state, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = plants.toggle_today_state("Léa")
    assert result == {}
    call = mock_table.update_item.call_args[1]
    assert "REMOVE watering" in call["UpdateExpression"]


@patch("src.plants.today_key", return_value="plant:2026-06-01")
@patch("src.plants.get_today_state",
       return_value={"state": "needs", "by": "Léa", "at": "..."})
@patch("src.plants._get_table")
def test_toggle_today_state_treats_legacy_needs_as_watered(
    mock_get_table, _state, _key,
):
    """Pre-revision rows with state='needs' should be clearable like new ones."""
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = plants.toggle_today_state("Léa")
    assert result == {}
    call = mock_table.update_item.call_args[1]
    assert "REMOVE watering" in call["UpdateExpression"]


def test_is_watered_helper():
    assert plants.is_watered({"state": "watered"}) is True
    assert plants.is_watered({"state": "needs"}) is True  # legacy
    assert plants.is_watered({}) is False
    assert plants.is_watered({"state": "ok"}) is False  # legacy negative
    assert plants.is_watered({"state": "bogus"}) is False


def test_today_key_format():
    key = plants.today_key()
    assert key.startswith("plant:")
    # Format YYYY-MM-DD
    date_part = key.split(":", 1)[1]
    parts = date_part.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 4


# --- get_last_watered_date tests ---


def _fake_rows(rows):
    """Return a get_item side_effect that serves the given rows by key.

    `rows` is a dict mapping date string ('2026-06-01') to a watering payload
    (or None for an empty row).
    """
    def side_effect(**kwargs):
        key = kwargs["Key"]["week_key"]
        date_str = key.split(":", 1)[1]
        if date_str in rows and rows[date_str] is not None:
            return {"Item": {"watering": rows[date_str]}}
        return {}
    return side_effect


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_no_rows(mock_dt, mock_get_table):
    mock_dt.date.today.return_value = datetime.date(2026, 6, 3)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    assert plants.get_last_watered_date() is None


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_today_watered(mock_dt, mock_get_table):
    mock_dt.date.today.return_value = datetime.date(2026, 6, 3)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _fake_rows({
        "2026-06-03": {"state": "watered", "by": "Léa", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    assert plants.get_last_watered_date() == datetime.date(2026, 6, 3)


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_legacy_needs_state(mock_dt, mock_get_table):
    """Pre-revision rows with state='needs' still count toward the cooldown."""
    mock_dt.date.today.return_value = datetime.date(2026, 6, 3)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _fake_rows({
        "2026-06-02": {"state": "needs", "by": "Timon", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    assert plants.get_last_watered_date() == datetime.date(2026, 6, 2)


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_today_ok_only(mock_dt, mock_get_table):
    """'ok' votes don't count as watered days."""
    mock_dt.date.today.return_value = datetime.date(2026, 6, 3)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _fake_rows({
        "2026-06-03": {"state": "ok", "by": "Timon", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    assert plants.get_last_watered_date() is None


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_yesterday_watered(mock_dt, mock_get_table):
    mock_dt.date.today.return_value = datetime.date(2026, 6, 3)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _fake_rows({
        "2026-06-02": {"state": "watered", "by": "Léa", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    assert plants.get_last_watered_date() == datetime.date(2026, 6, 2)


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_picks_most_recent(mock_dt, mock_get_table):
    """When multiple watered rows exist, return the most recent."""
    mock_dt.date.today.return_value = datetime.date(2026, 6, 3)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _fake_rows({
        "2026-06-03": {"state": "watered", "by": "Léa", "at": "..."},
        "2026-05-31": {"state": "watered", "by": "Timon", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    assert plants.get_last_watered_date() == datetime.date(2026, 6, 3)


@patch("src.plants._get_table")
@patch("src.plants.datetime")
def test_get_last_watered_date_respects_lookback(mock_dt, mock_get_table):
    """Rows older than lookback_days are ignored."""
    mock_dt.date.today.return_value = datetime.date(2026, 6, 10)
    mock_dt.timedelta = datetime.timedelta
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _fake_rows({
        "2026-06-01": {"state": "watered", "by": "Léa", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    # lookback_days=5 means we check today..today-5, so 06-05..06-10.
    # 06-01 is outside the window.
    assert plants.get_last_watered_date(lookback_days=5) is None
