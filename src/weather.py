import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

ZURICH_LAT = 47.37
ZURICH_LON = 8.55
HOT_THRESHOLD_C = 25.0
HTTP_TIMEOUT_S = 2.0

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={ZURICH_LAT}&longitude={ZURICH_LON}"
    "&daily=temperature_2m_max"
    "&timezone=Europe%2FZurich"
    "&forecast_days=1"
)


def get_zurich_max_temp_today():
    """Return today's forecast max temperature in Zurich (°C), or None on failure.

    Returning None lets callers skip silently rather than crash the Lambda.
    """
    try:
        with urllib.request.urlopen(OPEN_METEO_URL, timeout=HTTP_TIMEOUT_S) as resp:
            payload = json.loads(resp.read())
        return float(payload["daily"]["temperature_2m_max"][0])
    except (urllib.error.URLError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.warning("Open-Meteo fetch failed: %s", e)
        return None
