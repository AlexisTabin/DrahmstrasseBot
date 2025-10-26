import os
import datetime
import pytest
from unittest.mock import patch


import src.utils as utils


def test_get_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "dummy_token")
    token = utils.get_token()
    assert token == "dummy_token"


def test_get_group_id(monkeypatch):
    monkeypatch.setenv("BOT_CHAT_ID", "123456")
    group_id = utils.get_group_id()
    assert group_id == "123456"


def test_is_even_week_even():
    fake_date = datetime.datetime(2023, 10, 18)  # week 42 → even
    with patch("src.utils.datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = fake_date
        assert utils.is_even_week() is True

def test_is_even_week_odd():
    fake_date = datetime.datetime(2023, 10, 25)  # week 43 → odd
    with patch("src.utils.datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = fake_date
        assert utils.is_even_week() is False


