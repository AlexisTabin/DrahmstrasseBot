import io
import json
import urllib.error
from unittest.mock import patch

from src import weather


def _fake_resp(payload):
    body = io.BytesIO(json.dumps(payload).encode())

    class _Ctx:
        def __enter__(self_inner):
            return body

        def __exit__(self_inner, *a):
            return False

    return _Ctx()


@patch("src.weather.urllib.request.urlopen")
def test_get_zurich_max_temp_today_ok(mock_urlopen):
    mock_urlopen.return_value = _fake_resp({
        "daily": {"temperature_2m_max": [28.4]}
    })
    assert weather.get_zurich_max_temp_today() == 28.4


@patch("src.weather.urllib.request.urlopen")
def test_get_zurich_max_temp_today_network_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("boom")
    assert weather.get_zurich_max_temp_today() is None


@patch("src.weather.urllib.request.urlopen")
def test_get_zurich_max_temp_today_malformed(mock_urlopen):
    mock_urlopen.return_value = _fake_resp({"daily": {}})
    assert weather.get_zurich_max_temp_today() is None


@patch("src.weather.urllib.request.urlopen")
def test_get_zurich_max_temp_today_empty_array(mock_urlopen):
    mock_urlopen.return_value = _fake_resp({
        "daily": {"temperature_2m_max": []}
    })
    assert weather.get_zurich_max_temp_today() is None
