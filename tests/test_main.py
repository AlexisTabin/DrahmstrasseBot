import json
import pytest
from unittest.mock import patch, MagicMock
from src import main  # replace with actual module

def test_lambda_handler_with_body_success():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        event = {"body": '{"message":"test"}'}
        context = {}

        response = main.lambda_handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(event["body"])
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == "ok"


def test_lambda_handler_with_body_exception():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update.side_effect = Exception("fail")
        event = {"body": '{"message":"test"}'}
        context = {}

        response = main.lambda_handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(event["body"])
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == "ok"


def test_lambda_handler_without_body():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        event = {}  # no body
        context = {}

        response = main.lambda_handler(event, context)

        mock_bot_instance.process_update.assert_not_called()
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == "ok"

