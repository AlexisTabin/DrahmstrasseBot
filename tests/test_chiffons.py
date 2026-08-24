import datetime

import pytest
from unittest.mock import MagicMock, patch

from src import chiffons


@pytest.fixture(autouse=True)
def reset_table_cache():
    """Reset the cached table between tests."""
    chiffons._table = None
    yield
    chiffons._table = None


@patch("src.chiffons._current_week_key", return_value="chiffons:2026-W14")
@patch("src.chiffons._get_table")
def test_get_week_state_empty(mock_get_table, _key):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    assert chiffons.get_week_state() == {}


@patch("src.chiffons._current_week_key", return_value="chiffons:2026-W14")
@patch("src.chiffons._get_table")
def test_get_week_state_with_data(mock_get_table, _key):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {
            "week_key": "chiffons:2026-W14",
            "chiffons": {"by": "Léa", "at": "2026-04-01T10:00:00+00:00"},
        }
    }
    mock_get_table.return_value = mock_table

    assert chiffons.get_week_state()["by"] == "Léa"


@patch("src.chiffons._current_week_key", return_value="chiffons:2026-W14")
@patch("src.chiffons.get_week_state", return_value={})
@patch("src.chiffons._get_table")
def test_toggle_week_state_sets_it(mock_get_table, _state, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    state = chiffons.toggle_week_state("Alexis")

    assert state["by"] == "Alexis"
    assert "at" in state
    call = mock_table.update_item.call_args[1]
    assert call["UpdateExpression"] == "SET chiffons = :val"
    assert call["Key"] == {"week_key": "chiffons:2026-W14"}


@patch("src.chiffons._current_week_key", return_value="chiffons:2026-W14")
@patch("src.chiffons.get_week_state", return_value={"by": "Alexis", "at": "..."})
@patch("src.chiffons._get_table")
def test_toggle_week_state_clears_it(mock_get_table, _state, _key):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    assert chiffons.toggle_week_state("Alexis") == {}
    call = mock_table.update_item.call_args[1]
    assert call["UpdateExpression"] == "REMOVE chiffons"


# --- get_last_done: the "de temps en temps" bit ---


def _rows(found):
    """get_item side effect serving `found` (week_key -> state), {} elsewhere."""
    def side_effect(Key):
        state = found.get(Key["week_key"])
        return {"Item": {"week_key": Key["week_key"], "chiffons": state}} if state else {}
    return side_effect


@patch("src.chiffons.datetime", wraps=datetime)
@patch("src.chiffons._get_table")
def test_get_last_done_finds_the_most_recent_past_week(mock_get_table, mock_dt):
    mock_dt.date.today.return_value = datetime.date(2026, 5, 12)  # 2026-W20
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _rows({
        "chiffons:2026-W18": {"by": "Timon", "at": "..."},
        "chiffons:2026-W16": {"by": "Léa", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    weeks_ago, state = chiffons.get_last_done()
    assert (weeks_ago, state["by"]) == (2, "Timon")  # W18, not the older W16


@patch("src.chiffons.datetime", wraps=datetime)
@patch("src.chiffons._get_table")
def test_get_last_done_skips_the_current_week(mock_get_table, mock_dt):
    """get_week_state already answers for this week; this is the "and before
    that?" question."""
    mock_dt.date.today.return_value = datetime.date(2026, 5, 12)
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _rows({
        "chiffons:2026-W20": {"by": "Timon", "at": "..."},
    })
    mock_get_table.return_value = mock_table

    assert chiffons.get_last_done() is None


@patch("src.chiffons.datetime", wraps=datetime)
@patch("src.chiffons._get_table")
def test_get_last_done_gives_up_past_the_lookback(mock_get_table, mock_dt):
    mock_dt.date.today.return_value = datetime.date(2026, 5, 12)
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _rows({
        "chiffons:2026-W10": {"by": "Timon", "at": "..."},  # 10 weeks back
    })
    mock_get_table.return_value = mock_table

    assert chiffons.get_last_done() is None
    assert mock_table.get_item.call_count == chiffons.LOOKBACK_WEEKS


@patch("src.chiffons.datetime", wraps=datetime)
@patch("src.chiffons._get_table")
def test_week_keys_cross_the_year_boundary(mock_get_table, mock_dt):
    """Stepping back by weeks, not by week numbers, so January doesn't look
    for week -3."""
    mock_dt.date.today.return_value = datetime.date(2026, 1, 8)  # 2026-W02
    mock_table = MagicMock()
    mock_table.get_item.side_effect = _rows({})
    mock_get_table.return_value = mock_table

    chiffons.get_last_done(lookback_weeks=3)

    keys = [call[1]["Key"]["week_key"] for call in mock_table.get_item.call_args_list]
    assert keys == ["chiffons:2026-W01", "chiffons:2025-W52", "chiffons:2025-W51"]
