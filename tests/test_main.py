import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src import main  # replace with actual module

@pytest.mark.asyncio
async def test_lambda_handler_with_body_success():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()
        event = {"body": '{"message":"test"}'}
        context = {}

        response = await main.lambda_handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(event["body"])
        assert response["statusCode"] == 200

@pytest.mark.asyncio
async def test_lambda_handler_with_body_exception():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update.side_effect = Exception("fail")
        event = {"body": '{"message":"test"}'}
        context = {}

        response = await main.lambda_handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(event["body"])
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == "ok"


@pytest.mark.asyncio
async def test_lambda_handler_without_body():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        event = {}  # no body
        context = {}

        response = await main.lambda_handler(event, context)

        mock_bot_instance.process_update.assert_not_called()
        assert response["statusCode"] == 200


