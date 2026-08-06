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


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={})
def test_get_thursday_reminder_all_pending(mock_status, mock_holiday):
    from src.phrases import THURSDAY_REMINDER_HEADER
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert any(h in result for h in THURSDAY_REMINDER_HEADER)
    assert "CUISINE" in result
    assert "SDBs" in result


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"by": "Léa", "at": "..."},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_get_thursday_reminder_all_done(mock_status, mock_holiday):
    from src.phrases import THURSDAY_ALL_DONE
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert result in THURSDAY_ALL_DONE


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
def test_get_thursday_reminder_partial(mock_status, mock_holiday):
    from src.phrases import THURSDAY_REMINDER_HEADER
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert "CUISINE" in result
    assert "SDBs" in result
    assert any(h in result for h in THURSDAY_REMINDER_HEADER)


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
def test_get_sunday_recap(mock_status, mock_holiday):
    from src.phrases import SUNDAY_RECAP_HEADER
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert any(h in result for h in SUNDAY_RECAP_HEADER)
    assert "CUISINE" in result
    assert "fait par Timon" in result
    assert "pas fait" in result  # other roles not done


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"by": "Léa", "at": "..."},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_get_sunday_recap_all_done(mock_status, mock_holiday):
    from src.phrases import SUNDAY_RECAP_HEADER
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert any(h in result for h in SUNDAY_RECAP_HEADER)
    assert "pas fait" not in result


@patch("src.chores._get_table")
def test_get_stats_empty(mock_get_table):
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}
    mock_get_table.return_value = mock_table

    from src.phrases import STATS_EMPTY
    result = chores.get_stats()
    assert result in STATS_EMPTY


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

    from src.phrases import STATS_HEADER
    result = chores.get_stats()
    assert any(h in result for h in STATS_HEADER)
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

    from src.phrases import STATS_EMPTY
    result = chores.get_stats()
    assert result in STATS_EMPTY


# --- Holiday state tests ---


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_get_holiday_people_empty(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_get_table.return_value = mock_table

    assert chores.get_holiday_people() == set()


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_get_holiday_people_with_data(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {"week_key": "2026-W14", "vacances": {"Timon", "Léa"}},
    }
    mock_get_table.return_value = mock_table

    assert chores.get_holiday_people() == {"Timon", "Léa"}


@patch("src.chores.get_holiday_people", return_value={"Timon"})
def test_is_on_holiday_true(mock_holiday):
    assert chores.is_on_holiday("Timon") is True


@patch("src.chores.get_holiday_people", return_value={"Timon"})
def test_is_on_holiday_false(mock_holiday):
    assert chores.is_on_holiday("Léa") is False


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_set_on_holiday_adds_to_set(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    chores.set_on_holiday("Timon")

    mock_table.update_item.assert_called_once_with(
        Key={"week_key": "2026-W14"},
        UpdateExpression="ADD vacances :person",
        ExpressionAttributeValues={":person": {"Timon"}},
    )


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_cancel_holiday_removes_from_set(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table

    chores.cancel_holiday("Timon")

    mock_table.update_item.assert_called_once_with(
        Key={"week_key": "2026-W14"},
        UpdateExpression="DELETE vacances :person",
        ExpressionAttributeValues={":person": {"Timon"}},
    )


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
    assert "manque" in result
    assert "aspirateur" in result
    assert "panosse" in result


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


# --- _helper_lines tests ---


ALL_COLOCATAIRES = ["Timon", "Maël", "Léa", "Alexis"]


def test_helper_lines_empty_when_no_subtasks():
    assert chores._helper_lines("CUISINE", "Timon", {}, set(), ALL_COLOCATAIRES) == []


def test_helper_lines_empty_when_only_assigned_person_did_it():
    role_data = {"subtasks": {"frigo": {"by": "Timon", "at": "..."}}}
    assert chores._helper_lines("CUISINE", "Timon", role_data, set(), ALL_COLOCATAIRES) == []


def test_helper_lines_flags_someone_else():
    role_data = {"subtasks": {"frigo": {"by": "Léa", "at": "..."}}}
    lines = chores._helper_lines("CUISINE", "Timon", role_data, set(), ALL_COLOCATAIRES)
    assert len(lines) == 1
    assert "frigo" in lines[0]
    assert "Léa" in lines[0]
    assert "Timon" in lines[0]


def test_helper_lines_only_flags_the_non_assigned_subtasks():
    role_data = {"subtasks": {
        "frigo": {"by": "Léa", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
    }}
    lines = chores._helper_lines("CUISINE", "Timon", role_data, set(), ALL_COLOCATAIRES)
    assert len(lines) == 1
    assert "frigo" in lines[0]


def test_helper_lines_no_flag_when_holiday_redistribution_matches():
    """If Timon is on holiday and frigo was redistributed to Léa, Léa doing
    frigo is expected, not a 'helper' — it shouldn't be flagged."""
    role_data = {"subtasks": {"frigo": {"by": "Léa", "at": "..."}}}
    with patch(
        "src.menage.get_holiday_redistribution",
        return_value={"frigo": "Léa", "plan de travail": "Alexis", "rangement": "Alexis"},
    ):
        lines = chores._helper_lines(
            "CUISINE", "Timon", role_data, {"Timon"}, ALL_COLOCATAIRES,
        )
    assert lines == []


def test_helper_lines_skips_subtask_without_by():
    """Defensive: a subtask entry with no 'by' (shouldn't happen in practice,
    since toggle_subtask always sets it) is simply skipped, not a crash."""
    role_data = {"subtasks": {"frigo": {"at": "..."}}}
    lines = chores._helper_lines("CUISINE", "Timon", role_data, set(), ALL_COLOCATAIRES)
    assert lines == []


# --- get_sunday_recap with helper credit ---


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "frigo": {"by": "Léa", "at": "..."},
        "plan de travail": {"by": "Timon", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
    }},
})
def test_get_sunday_recap_credits_helper_on_complete_role(mock_status, mock_holiday):
    """CUISINE is fully done, but Léa (not the assigned Timon) did the fridge."""
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "CUISINE" in result
    assert "frigo fait par Léa" in result
    assert "pas Timon" in result


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "SDBs": {"subtasks": {
        "petit WC": {"by": "Alexis", "at": "..."},
    }},
})
def test_get_sunday_recap_credits_helper_on_incomplete_role(mock_status, mock_holiday):
    """SDBs isn't fully done, but someone other than Maël already helped."""
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "SDBs" in result
    assert "pas fait" in result
    assert "petit WC fait par Alexis" in result


# --- reminder/recap with subtask format ---


@patch("src.chores.get_holiday_people", return_value=set())
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
def test_thursday_reminder_with_subtasks(mock_even, mock_status, mock_holiday):
    from src.phrases import THURSDAY_DONE_SECTION
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    # DÉCHETS is not fully done (only poubelle of 5)
    assert "DÉCHETS" in result
    assert "manque" in result
    # SOLs is fully done
    assert any(s in result for s in THURSDAY_DONE_SECTION)


@patch("src.chores.get_holiday_people", return_value=set())
@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"subtasks": {
        "aspirateur": {"by": "Léa", "at": "..."},
        "panosse": {"by": "Léa", "at": "..."},
    }},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_sunday_recap_mixed_formats(mock_status, mock_holiday):
    from src.phrases import SUNDAY_RECAP_HEADER
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert any(h in result for h in SUNDAY_RECAP_HEADER)
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
