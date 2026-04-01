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

        response = await main.handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(json.loads(event["body"]))
        assert response["statusCode"] == 200

@pytest.mark.asyncio
async def test_lambda_handler_with_body_exception():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock(side_effect=Exception("fail"))
        mock_bot_instance.dev_chat_id = "123456"
        mock_bot_instance.bot = MagicMock()
        mock_bot_instance.bot.send_message = AsyncMock()
        event = {"body": '{"message":"test"}'}
        context = {}

        response = await main.handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(json.loads(event["body"]))
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == "ok"
        mock_bot_instance.bot.send_message.assert_called_once()
        call_args = mock_bot_instance.bot.send_message.call_args
        assert call_args[0][0] == "123456"
        assert "fail" in call_args[0][1]
        assert "<pre>" in call_args[0][1]
        assert call_args[1]["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_lambda_handler_exception_notification_failure_does_not_crash():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock(side_effect=Exception("fail"))
        mock_bot_instance.dev_chat_id = "123456"
        mock_bot_instance.bot = MagicMock()
        mock_bot_instance.bot.send_message = AsyncMock(side_effect=Exception("telegram down"))
        event = {"body": '{"message":"test"}'}
        context = {}

        response = await main.handler(event, context)

        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == "ok"


@pytest.mark.asyncio
async def test_lambda_handler_exception_no_dev_chat_id():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock(side_effect=Exception("fail"))
        mock_bot_instance.dev_chat_id = None
        mock_bot_instance.bot = MagicMock()
        mock_bot_instance.bot.send_message = AsyncMock()
        event = {"body": '{"message":"test"}'}
        context = {}

        response = await main.handler(event, context)

        assert response["statusCode"] == 200
        mock_bot_instance.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_lambda_handler_without_body():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        event = {}  # no body
        context = {}

        response = await main.handler(event, context)

        mock_bot_instance.process_update.assert_not_called()
        assert response["statusCode"] == 200
