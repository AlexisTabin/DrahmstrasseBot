import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src import main  # replace with actual module

@pytest.mark.asyncio
async def test_lambda_handler_with_body_success():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()
        event = {"body": '{"update_id": 1, "message":"test"}'}
        context = {}

        response = await main.handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(
            {"update_id": 1, "message": "test"}
        )
        assert response["statusCode"] == 200

@pytest.mark.asyncio
async def test_lambda_handler_eventbridge_payload_adds_missing_fields():
    """EventBridge fake payloads lack update_id/message_id/date that telebot requires."""
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()

        # Exactly what EventBridge sends — no update_id, no message_id, no date
        eventbridge_body = {
            "message": {
                "chat": {"id": -1001633433047},
                "text": "/carton@DrahmstrasseBot",
                "entities": [{"type": "bot_command", "offset": 0, "length": 23}],
            }
        }
        event = {"body": json.dumps(eventbridge_body)}

        response = await main.handler(event, {})

        # The handler must inject all fields that telebot requires.
        # Chat requires both 'id' and 'type' per the Telegram Bot API;
        # Message requires 'message_id' and 'date'; Update requires 'update_id'.
        called_body = mock_bot_instance.process_update.call_args[0][0]
        assert called_body["update_id"] == 0
        assert called_body["message"]["message_id"] == 0
        assert called_body["message"]["date"] == 0
        assert called_body["message"]["chat"]["type"] == "group"
        assert response["statusCode"] == 200


@pytest.mark.asyncio
async def test_eventbridge_payload_deserialization_requires_chat_type():
    """Reproduce: EventBridge payloads missing chat.type cause TypeError in telebot."""
    import telebot

    # Exactly what main.py passes to process_update after injecting
    # update_id / message_id / date — but chat still has no 'type'.
    payload = {
        "update_id": 0,
        "message": {
            "message_id": 0,
            "date": 0,
            "chat": {"id": -1001633433047},
            "text": "/roles@DrahmstrasseBot",
            "entities": [{"type": "bot_command", "offset": 0, "length": 22}],
        },
    }

    with pytest.raises(TypeError, match="missing 1 required positional argument: 'type'"):
        telebot.types.Update.de_json(payload)


@pytest.mark.asyncio
async def test_lambda_handler_with_body_exception():
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock(side_effect=Exception("fail"))
        mock_bot_instance.dev_chat_id = "123456"
        mock_bot_instance.bot = MagicMock()
        mock_bot_instance.bot.send_message = AsyncMock()
        event = {"body": '{"update_id": 1, "message":"test"}'}
        context = {}

        response = await main.handler(event, context)

        mock_bot_instance.process_update.assert_called_once_with(
            {"update_id": 1, "message": "test"}
        )
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
        event = {"body": '{"update_id": 1, "message":"test"}'}
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
        event = {"body": '{"update_id": 1, "message":"test"}'}
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


@pytest.mark.asyncio
async def test_lambda_handler_webhook_with_valid_secret(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()
        event = {
            "headers": {"x-telegram-bot-api-secret-token": "s3cret"},
            "body": '{"update_id": 1, "message": "test"}',
        }

        response = await main.handler(event, {})

        mock_bot_instance.process_update.assert_called_once()
        assert response["statusCode"] == 200


@pytest.mark.asyncio
async def test_lambda_handler_webhook_with_wrong_secret_rejected(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()
        event = {
            "headers": {"x-telegram-bot-api-secret-token": "wrong"},
            "body": '{"update_id": 1, "message": "test"}',
        }

        response = await main.handler(event, {})

        mock_bot_instance.process_update.assert_not_called()
        assert response["statusCode"] == 401


@pytest.mark.asyncio
async def test_lambda_handler_webhook_without_secret_header_rejected(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()
        event = {
            "headers": {"content-type": "application/json"},
            "body": '{"update_id": 1, "message": "test"}',
        }

        response = await main.handler(event, {})

        mock_bot_instance.process_update.assert_not_called()
        assert response["statusCode"] == 401


@pytest.mark.asyncio
async def test_lambda_handler_eventbridge_skips_secret_check(monkeypatch):
    """EventBridge events have no 'headers' and must pass through without a secret."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    with patch("src.main.Drahmbot") as MockDrahmbot:
        mock_bot_instance = MockDrahmbot.return_value
        mock_bot_instance.process_update = AsyncMock()
        event = {"body": '{"update_id": 1, "message": "test"}'}  # no 'headers' key

        response = await main.handler(event, {})

        mock_bot_instance.process_update.assert_called_once()
        assert response["statusCode"] == 200
