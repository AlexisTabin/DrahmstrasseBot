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


@patch("src.chores._get_table")
def test_get_stats_empty(mock_get_table):
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}
    mock_get_table.return_value = mock_table

    result = chores.get_stats()
    assert result == "Pas encore de stats !"


@patch("src.chores._get_table")
def test_get_stats_multiple_weeks(mock_get_table):
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {
                "week_key": "2026-W10",
                "completed": {
                    "CUISINE": {"by": "Timon", "at": "..."},
                    "SDBs": {"by": "Maël", "at": "..."},
                },
            },
            {
                "week_key": "2026-W11",
                "completed": {
                    "CUISINE": {"by": "Timon", "at": "..."},
                    "SOLs": {"by": "Léa", "at": "..."},
                    "DÉCHETS": {"by": "Timon", "at": "..."},
                },
            },
            {
                "week_key": "2026-W12",
                "completed": {
                    "CUISINE": {"by": "Maël", "at": "..."},
                },
            },
        ]
    }
    mock_get_table.return_value = mock_table

    result = chores.get_stats()
    assert "Stats :" in result
    # Timon: 3 (W10 CUISINE, W11 CUISINE, W11 DÉCHETS)
    assert "Timon : 3 tâches" in result
    # Maël: 2 (W10 SDBs, W12 CUISINE)
    assert "Maël : 2 tâches" in result
    # Léa: 1 (W11 SOLs)
    assert "Léa : 1 tâches" in result
    # Timon should be first (gold medal)
    assert "🥇" in result
    lines = result.split("\n")
    # First person line (index 1) should be Timon
    assert "Timon" in lines[1]


@patch("src.chores._get_table")
def test_get_stats_no_completed_field(mock_get_table):
    """Items with no completed map are handled gracefully."""
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {"week_key": "2026-W10"},
        ]
    }
    mock_get_table.return_value = mock_table

    result = chores.get_stats()
    assert result == "Pas encore de stats !"


# --- toggle_role tests ---


@patch("src.chores.get_week_status", return_value={})
@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_toggle_role_on(mock_get_table, mock_week, mock_status):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = chores.toggle_role("CUISINE", "Timon")
    assert result is True
    # 1 call to ensure map + 1 call to SET role
    assert mock_table.update_item.call_count == 2


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_toggle_role_off(mock_get_table, mock_week, mock_status):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = chores.toggle_role("CUISINE", "Timon")
    assert result is False
    # 1 call to ensure map + 1 call to REMOVE role
    assert mock_table.update_item.call_count == 2
    last_call = mock_table.update_item.call_args_list[1][1]
    assert "REMOVE" in last_call["UpdateExpression"]


# --- toggle_subtask tests ---


@patch("src.chores.get_week_status", return_value={})
@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_toggle_subtask_on(mock_get_table, mock_week, mock_status):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = chores.toggle_subtask("DÉCHETS", "poubelle", "Alexis")
    assert result is True
    # 1 ensure map + 1 ensure role subtasks + 1 SET subtask
    assert mock_table.update_item.call_count == 3


@patch("src.chores.get_week_status", return_value={
    "DÉCHETS": {"subtasks": {"poubelle": {"by": "Alexis", "at": "..."}}},
})
@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_toggle_subtask_off(mock_get_table, mock_week, mock_status):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    result = chores.toggle_subtask("DÉCHETS", "poubelle", "Alexis")
    assert result is False
    # 1 ensure map + 1 ensure role subtasks + 1 REMOVE subtask
    assert mock_table.update_item.call_count == 3
    last_call = mock_table.update_item.call_args_list[2][1]
    assert "REMOVE" in last_call["UpdateExpression"]


# --- is_role_complete tests ---


def test_is_role_complete_missing():
    assert chores.is_role_complete("CUISINE", {}) is False


def test_is_role_complete_old_format():
    completed = {"CUISINE": {"by": "Timon", "at": "..."}}
    assert chores.is_role_complete("CUISINE", completed) is True


@patch("src.menage.is_even_week", return_value=False)
def test_is_role_complete_subtasks_all_done(mock_even):
    completed = {
        "SOLs": {
            "subtasks": {
                "aspirateur": {"by": "Léa", "at": "..."},
                "panosse": {"by": "Léa", "at": "..."},
            }
        }
    }
    assert chores.is_role_complete("SOLs", completed) is True


@patch("src.menage.is_even_week", return_value=False)
def test_is_role_complete_subtasks_partial(mock_even):
    completed = {
        "SOLs": {
            "subtasks": {
                "aspirateur": {"by": "Léa", "at": "..."},
            }
        }
    }
    assert chores.is_role_complete("SOLs", completed) is False


@patch("src.menage.is_even_week", return_value=True)
def test_is_role_complete_dechets_even_week_needs_papier(mock_even):
    completed = {
        "DÉCHETS": {
            "subtasks": {
                "poubelle": {"by": "Alexis", "at": "..."},
                "carton": {"by": "Alexis", "at": "..."},
                "compost": {"by": "Alexis", "at": "..."},
                "verre": {"by": "Alexis", "at": "..."},
                "plastique": {"by": "Alexis", "at": "..."},
            }
        }
    }
    # Missing papier on even week → not complete
    assert chores.is_role_complete("DÉCHETS", completed) is False


# --- _pending_detail tests ---


@patch("src.menage.is_even_week", return_value=False)
def test_pending_detail_with_missing(mock_even):
    completed = {
        "SOLs": {
            "subtasks": {
                "aspirateur": {"by": "Léa", "at": "..."},
            }
        }
    }
    result = chores._pending_detail("SOLs", completed)
    assert "panosse" in result
    assert "manque" in result


def test_pending_detail_role_not_started():
    result = chores._pending_detail("SOLs", {})
    assert result == ""


def test_pending_detail_old_format():
    completed = {"CUISINE": {"by": "Timon", "at": "..."}}
    result = chores._pending_detail("CUISINE", completed)
    assert result == ""


# --- _who_did_it tests ---


def test_who_did_it_old_format():
    assert chores._who_did_it({"by": "Timon", "at": "..."}) == "Timon"


def test_who_did_it_subtask_format():
    role_data = {
        "subtasks": {
            "aspirateur": {"by": "Léa", "at": "..."},
            "panosse": {"by": "Léa", "at": "..."},
        }
    }
    assert chores._who_did_it(role_data) == "Léa"


def test_who_did_it_empty():
    assert chores._who_did_it({}) == "?"


# --- reminder/recap with subtask format ---


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"subtasks": {
        "aspirateur": {"by": "Léa", "at": "..."},
        "panosse": {"by": "Léa", "at": "..."},
    }},
    "DÉCHETS": {"subtasks": {
        "poubelle": {"by": "Alexis", "at": "..."},
    }},
})
@patch("src.menage.is_even_week", return_value=False)
def test_thursday_reminder_with_subtasks(mock_even, mock_status):
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    # DÉCHETS is not fully done (only poubelle of 5)
    assert "DÉCHETS" in result
    assert "manque" in result
    # SOLs is fully done
    assert "Déjà fait" in result


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"subtasks": {
        "aspirateur": {"by": "Léa", "at": "..."},
        "panosse": {"by": "Léa", "at": "..."},
    }},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_sunday_recap_mixed_formats(mock_status):
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "Récap" in result
    assert "fait par Timon" in result
    assert "fait par Léa" in result
    assert "fait par Alexis" in result
    assert "pas fait" not in result


# --- stats with subtask format ---


@patch("src.menage.is_even_week", return_value=False)
@patch("src.chores._get_table")
def test_get_stats_with_subtask_format(mock_get_table, mock_even):
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {
                "week_key": "2026-W14",
                "completed": {
                    "CUISINE": {"by": "Timon", "at": "..."},
                    "SOLs": {"subtasks": {
                        "aspirateur": {"by": "Léa", "at": "..."},
                        "panosse": {"by": "Léa", "at": "..."},
                    }},
                    "DÉCHETS": {"subtasks": {
                        "poubelle": {"by": "Alexis", "at": "..."},
                    }},
                },
            },
        ]
    }
    mock_get_table.return_value = mock_table

    result = chores.get_stats()
    # Timon: 1 (CUISINE old format)
    assert "Timon : 1 tâches" in result
    # Léa: 1 (SOLs fully complete)
    assert "Léa : 1 tâches" in result
    # Alexis: 0 (DÉCHETS not fully complete — only 1 of 5 subtasks)
    assert "Alexis" not in result
