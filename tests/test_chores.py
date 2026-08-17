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


@patch("src.chores.get_week_status", return_value={})
def test_get_thursday_reminder_all_pending(mock_status):
    from src.phrases import THURSDAY_REMINDER_HEADER
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert any(h in result for h in THURSDAY_REMINDER_HEADER)
    assert "CUISINE" in result
    assert "SDBs" in result


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
    "SDBs": {"by": "Maël", "at": "..."},
    "SOLs": {"by": "Léa", "at": "..."},
    "DÉCHETS": {"by": "Alexis", "at": "..."},
})
def test_get_thursday_reminder_all_done(mock_status):
    from src.phrases import THURSDAY_ALL_DONE
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert result in THURSDAY_ALL_DONE


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
def test_get_thursday_reminder_partial(mock_status):
    from src.phrases import THURSDAY_REMINDER_HEADER
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    assert "CUISINE" in result
    assert "SDBs" in result
    assert any(h in result for h in THURSDAY_REMINDER_HEADER)


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
def test_get_sunday_recap(mock_status):
    from src.phrases import SUNDAY_RECAP_HEADER
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert any(h in result for h in SUNDAY_RECAP_HEADER)
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


def test_helper_lines_empty_when_no_subtasks():
    assert chores._helper_lines("Timon", {}) == []


def test_helper_lines_empty_when_only_assigned_person_did_it():
    role_data = {"subtasks": {"frigo": {"by": "Timon", "at": "..."}}}
    assert chores._helper_lines("Timon", role_data) == []


def test_helper_lines_flags_someone_else():
    role_data = {"subtasks": {"frigo": {"by": "Léa", "at": "..."}}}
    lines = chores._helper_lines("Timon", role_data)
    assert len(lines) == 1
    assert "frigo" in lines[0]
    assert "Léa" in lines[0]
    assert "Timon" in lines[0]


def test_helper_lines_only_flags_the_non_assigned_subtasks():
    role_data = {"subtasks": {
        "frigo": {"by": "Léa", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
    }}
    lines = chores._helper_lines("Timon", role_data)
    assert len(lines) == 1
    assert "frigo" in lines[0]


# --- get_sunday_recap with helper credit ---


@patch("src.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "frigo": {"by": "Léa", "at": "..."},
        "plan de travail": {"by": "Timon", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
    }},
})
def test_get_sunday_recap_credits_helper_on_complete_role(mock_status):
    """CUISINE is fully done, but Léa (not the assigned Timon) did the fridge."""
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "CUISINE" in result
    assert "frigo fait par Léa" in result
    assert "pas Timon" in result


@patch("src.chores.get_week_status", return_value={
    "SDBs": {"subtasks": {
        "petit WC": {"by": "Alexis", "at": "..."},
    }},
})
def test_get_sunday_recap_credits_helper_on_incomplete_role(mock_status):
    """SDBs isn't fully done, but someone other than Maël already helped."""
    result = chores.get_sunday_recap(SAMPLE_ASSIGNMENTS)
    assert "SDBs" in result
    assert "pas fait" in result
    assert "petit WC fait par Alexis" in result


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
    from src.phrases import THURSDAY_DONE_SECTION
    result = chores.get_thursday_reminder(SAMPLE_ASSIGNMENTS)
    # DÉCHETS is not fully done (only poubelle of 5)
    assert "DÉCHETS" in result
    assert "manque" in result
    # SOLs is fully done
    assert any(s in result for s in THURSDAY_DONE_SECTION)


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


# --- increment_subtask_counter tests ---


def _update_item_response(count):
    """Shape of the real DynamoDB ReturnValues='UPDATED_NEW' response our code reads."""
    return {
        "Attributes": {
            "completed": {"CUISINE": {"subtasks": {"plan de travail": {"count": count}}}},
        }
    }


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_increment_subtask_counter_first_press(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_table.update_item.return_value = _update_item_response(1)
    mock_get_table.return_value = mock_table

    result = chores.increment_subtask_counter("CUISINE", "plan de travail", "Timon")
    assert result == 1
    # 1 ensure map + 1 ensure role subtasks + 1 ensure counter + 1 increment
    assert mock_table.update_item.call_count == 4
    last_call = mock_table.update_item.call_args_list[3][1]
    assert "ADD" in last_call["UpdateExpression"]
    assert last_call["ExpressionAttributeValues"][":person"] == "Timon"
    assert last_call["ReturnValues"] == "UPDATED_NEW"
    # "by"/"at" are DynamoDB reserved words and must be aliased, not used raw.
    assert last_call["ExpressionAttributeNames"]["#by"] == "by"
    assert last_call["ExpressionAttributeNames"]["#at"] == "at"


@patch("src.chores._current_week_key", return_value="2026-W14")
@patch("src.chores._get_table")
def test_increment_subtask_counter_reads_back_new_count(mock_get_table, mock_week):
    mock_table = MagicMock()
    mock_table.update_item.return_value = _update_item_response(3)
    mock_get_table.return_value = mock_table

    result = chores.increment_subtask_counter("CUISINE", "plan de travail", "Léa")
    assert result == 3  # reflects the update_item response, not a separate read

    # Every increment tracks the doer in a "doers" set, not just the last "by".
    last_call = mock_table.update_item.call_args_list[3][1]
    assert last_call["ExpressionAttributeValues"][":person_set"] == {"Léa"}


# --- is_role_complete / _pending_detail with counter subtasks ---


def test_is_role_complete_counter_subtask_satisfied_by_any_count():
    completed = {
        "CUISINE": {
            "subtasks": {
                "frigo": {"by": "Timon", "at": "..."},
                "plan de travail": {"count": 1, "by": "Timon", "at": "..."},
                "rangement": {"by": "Timon", "at": "..."},
                "balcon": {"by": "Timon", "at": "..."},
            }
        }
    }
    assert chores.is_role_complete("CUISINE", completed) is True


def test_is_role_complete_missing_counter_subtask():
    completed = {
        "CUISINE": {
            "subtasks": {
                "frigo": {"by": "Timon", "at": "..."},
                "rangement": {"by": "Timon", "at": "..."},
                "balcon": {"by": "Timon", "at": "..."},
            }
        }
    }
    assert chores.is_role_complete("CUISINE", completed) is False


def test_pending_detail_lists_missing_counter_subtask():
    completed = {
        "CUISINE": {
            "subtasks": {
                "frigo": {"by": "Timon", "at": "..."},
                "rangement": {"by": "Timon", "at": "..."},
                "balcon": {"by": "Timon", "at": "..."},
            }
        }
    }
    result = chores._pending_detail("CUISINE", completed)
    assert "plan de travail" in result


# --- is_subtask_satisfied ---


def test_is_subtask_satisfied_toggle_shape_is_always_satisfied():
    assert chores.is_subtask_satisfied({"by": "Timon", "at": "..."}) is True


def test_is_subtask_satisfied_counter_with_positive_count():
    assert chores.is_subtask_satisfied({"count": 3, "by": "Timon", "at": "..."}) is True


def test_is_subtask_satisfied_counter_at_zero_is_not_satisfied():
    """A durable {"count": 0} entry (e.g. left by a crash between
    increment_subtask_counter's ensure-step and its increment-step) must not
    count as done."""
    assert chores.is_subtask_satisfied({"count": 0}) is False


def test_is_role_complete_counter_stuck_at_zero_is_not_complete():
    """Regression: a present-but-unsatisfied counter entry used to make the
    role look complete because is_role_complete only checked key presence."""
    completed = {
        "CUISINE": {
            "subtasks": {
                "frigo": {"by": "Timon", "at": "..."},
                "plan de travail": {"count": 0},
                "rangement": {"by": "Timon", "at": "..."},
                "balcon": {"by": "Timon", "at": "..."},
            }
        }
    }
    assert chores.is_role_complete("CUISINE", completed) is False


def test_pending_detail_lists_counter_stuck_at_zero_as_missing():
    completed = {
        "CUISINE": {
            "subtasks": {
                "frigo": {"by": "Timon", "at": "..."},
                "plan de travail": {"count": 0},
                "rangement": {"by": "Timon", "at": "..."},
                "balcon": {"by": "Timon", "at": "..."},
            }
        }
    }
    result = chores._pending_detail("CUISINE", completed)
    assert "plan de travail" in result


# --- multi-doer credit for counter subtasks ---


def test_who_did_it_counter_credits_every_doer():
    role_data = {
        "subtasks": {
            "plan de travail": {"count": 4, "by": "Timon", "at": "...", "doers": {"Léa", "Timon"}},
        }
    }
    assert chores._who_did_it(role_data) == "Léa, Timon"


def test_helper_lines_counter_flags_every_non_assigned_doer():
    """Timon is CUISINE this week; Léa and Maël both pitched in on the counter,
    but only the last incrementer used to be recorded via bare 'by'."""
    role_data = {
        "subtasks": {
            "plan de travail": {
                "count": 3, "by": "Maël", "at": "...", "doers": {"Léa", "Maël", "Timon"},
            },
        }
    }
    lines = chores._helper_lines("Timon", role_data)
    assert len(lines) == 1
    assert "Léa" in lines[0]
    assert "Maël" in lines[0]
    assert "Timon" not in lines[0].split("fait par")[1].split("(pas")[0]


@patch("src.menage.is_even_week", return_value=False)
@patch("src.chores._get_table")
def test_get_stats_counter_credits_every_doer_not_just_last(mock_get_table, mock_even):
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {
                "week_key": "2026-W14",
                "completed": {
                    "CUISINE": {"subtasks": {
                        "frigo": {"by": "Timon", "at": "..."},
                        "plan de travail": {
                            "count": 4, "by": "Timon", "at": "...", "doers": {"Léa", "Timon"},
                        },
                        "rangement": {"by": "Timon", "at": "..."},
                        "balcon": {"by": "Timon", "at": "..."},
                    }},
                },
            },
        ]
    }
    mock_get_table.return_value = mock_table

    result = chores.get_stats()
    assert "Timon : 1 tâches" in result
    assert "Léa : 1 tâches" in result


# --- stats: counter subtask only ever contributes once per week ---


@patch("src.chores._get_table")
def test_get_stats_counter_subtask_counts_once_regardless_of_count_value(mock_get_table):
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {
                "week_key": "2026-W14",
                "completed": {
                    "CUISINE": {"subtasks": {
                        "frigo": {"by": "Timon", "at": "..."},
                        "plan de travail": {"count": 5, "by": "Timon", "at": "..."},
                        "rangement": {"by": "Timon", "at": "..."},
                        "balcon": {"by": "Timon", "at": "..."},
                    }},
                },
            },
        ]
    }
    mock_get_table.return_value = mock_table

    result = chores.get_stats()
    # Timon gets 1 point for the complete CUISINE role, not 5 for the counter.
    assert "Timon : 1 tâches" in result
