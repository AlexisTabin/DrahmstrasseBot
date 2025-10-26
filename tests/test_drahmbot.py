import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.drahmbot import Drahmbot, colocataires

@pytest.mark.asyncio
async def test_singleton_behavior():
    bot1 = Drahmbot(token="12345:12345", chat_id=123)
    bot2 = Drahmbot(token="12345:12345", chat_id=456)
    assert bot1 is bot2
    assert bot1.chat_id == 123  # The first initialization should stick

@pytest.mark.asyncio
@patch("src.drahmbot.telebot.types.Update.de_json")
async def test_process_update(mock_de_json):
    bot = Drahmbot(token="12345:12345", chat_id=123)
    bot.bot.process_new_updates = AsyncMock()
    update_json = {"update_id": 1}
    mock_de_json.return_value = "mocked_update"
    await bot.process_update(update_json)
    bot.bot.process_new_updates.assert_called_with(["mocked_update"])


@pytest.mark.asyncio
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
@patch("src.drahmbot.menage.getRoles", return_value="Roles info")
@patch("src.drahmbot.menage.getCartonOrPapier", return_value="Papier info")
@patch("src.drahmbot.menage.getCarteDeLessive", return_value="Lessive info")
@patch("src.drahmbot.social.is_present_dinner", return_value="Who is here?")
async def test_bot_handlers(
    mock_who, mock_lessive, mock_papier, mock_roles, mock_group, mock_token
):
    bot = Drahmbot()  # Will use patched utils functions

    # Patch sending methods
    bot.bot.send_message = AsyncMock()
    bot.bot.send_poll = AsyncMock()
    bot.bot.reply_to = AsyncMock()

    # Call handlers directly by capturing them during registration
    handlers = {}

    # Patch the decorator to capture the functions
    original_message_handler = bot.bot.message_handler

    def capture_handler(*args, **kwargs):
        def wrapper(func):
            if "commands" in kwargs:
                for cmd in kwargs["commands"]:
                    handlers[cmd] = func
            if "regexp" in kwargs:
                handlers[kwargs["regexp"]] = func
            return func
        return wrapper

    bot.bot.message_handler = capture_handler
    bot.register_handlers()  # Re-register to capture

    # Simulate messages
    message = MagicMock()
    message.chat.id = 999

    # Call /roles
    await handlers["roles"](message)
    bot.bot.send_message.assert_called_with(999, "Roles info")

    # Call /papier
    await handlers["papier"](message)
    bot.bot.send_message.assert_called_with(999, "Papier info")

    # Call /lessive
    await handlers["lessive"](message)
    bot.bot.send_message.assert_called_with(999, "Lessive info")

    # Call /whoishere
    await handlers["whoishere"](message)
    bot.bot.send_poll.assert_called_with(
        999,
        "Who is here?",
        [
            "Oui",
            "Oui INTO je ramène un.e +1",
            "Oui INTO je cuisine",
            "Oui, je cuisine ET je ramène un.e +1",
            "C'est ciao",
        ],
        is_anonymous=False,
    )

    # Call regexp jeremie?
    await handlers["jeremie?"](message)
    bot.bot.reply_to.assert_called_with(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")

