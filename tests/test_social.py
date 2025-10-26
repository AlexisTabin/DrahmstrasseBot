import pytest
import datetime
from unittest.mock import patch

from src.social import is_present_dinner


def test_is_present_dinner_returns_expected_question():

    result = is_present_dinner()
    
    # Check the type and content
    assert isinstance(result, str)
    assert "SOUPER" in result
    assert result.startswith("Pouet")
    assert "AL pour le SOUPER ce soir" in result

