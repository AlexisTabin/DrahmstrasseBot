import pytest
from unittest.mock import patch, MagicMock

from src import chores


SAMPLE_ASSIGNMENTS = {
    "CUISINE": "Timon",
    "SDBs": "Maël",
    "SOLs": "Léa",
    "DÉCHETS": "Alexis",
}


@pytest.fixture(autouse=True)
def reset_table_cache():
    """Reset the cached table between tests."""
    chores._table = None
    yield
    chores._table = None


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_mark_done_new(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = chores.mark_done("CUISINE", "Timon")
    assert result is True
    # Two calls: first ensures map exists, second sets the role
    assert mock_table.update_item.call_count == 2
    call_kwargs = mock_table.update_item.call_args_list[1][1]
    assert call_kwargs["Key"] == {"week_key": "2026-W14"}
    assert call_kwargs["ExpressionAttributeNames"] == {"#role": "CUISINE"}


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_mark_done_already_done(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_client = MagicMock()
    mock_table.meta.client = mock_client

    # Simulate ConditionalCheckFailedException on the second call only
    exc_class = type("ConditionalCheckFailedException", (Exception,), {})
    mock_client.exceptions.ConditionalCheckFailedException = exc_class
    # First call (ensure map) succeeds, second call (set role) fails
    mock_table.update_item.side_effect = [None, exc_class("already done")]
    mock_get_table.return_value = mock_table

    result = chores.mark_done("CUISINE", "Timon")
    assert result is False


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_get_week_status_empty(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    status = chores.get_week_status()
    assert status == {}


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_get_week_status_with_data(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {
            "week_key": "2026-W14",
            "completed": {"CUISINE": {"by": "Timon", "at": "2026-04-01T10:00:00Z"}},
        }
    }
    mock_get_table.return_value = mock_table

    status = chores.get_week_status()
    assert "CUISINE" in status
    assert status["CUISINE"]["by"] == "Timon"


@patch("src.chores.get_week_status", return_value={})
def test_get_thursday_reminder_all_pending(mock_status):
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert "Rappel du jeudi" in result
    assert "CUISINE" in result
    assert "SDBs" in result


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"by": "Léa", "at": "..."},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_get_thursday_reminder_all_done(mock_status):
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert "bravo" in result.lower()


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
def test_get_thursday_reminder_partial(mock_status):
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert "CUISINE" in result
    assert "SDBs" in result
    assert "Rappel du jeudi" in result


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
def test_get_sunday_recap(mock_status):
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "Récap" in result
    assert "CUISINE" in result
    assert "fait par Timon" in result
    assert "pas fait" in result  # other roles not done


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"by": "Léa", "at": "..."},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_get_sunday_recap_all_done(mock_status):
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "Récap" in result
    assert "pas fait" not in result
