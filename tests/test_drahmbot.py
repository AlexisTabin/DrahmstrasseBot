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


def _capture_handlers(bot):
    """Re-register handlers and capture them by command name."""
    handlers = {}
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
    bot.register_handlers()
    return handlers


@pytest.mark.asyncio
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
@patch("src.drahmbot.menage.getRoles", return_value="Roles info")
@patch("src.drahmbot.menage.get_papier_reminder", return_value="Papier reminder")
@patch("src.drahmbot.menage.getCarteDeLessive", return_value="Lessive info")
@patch("src.drahmbot.social.is_present_dinner", return_value="Who is here?")
async def test_bot_handlers(
    mock_who, mock_lessive, mock_papier, mock_roles, mock_group, mock_token
):
    bot = Drahmbot()

    bot.bot.send_message = AsyncMock()
    bot.bot.send_poll = AsyncMock()
    bot.bot.reply_to = AsyncMock()

    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    # /roles
    await handlers["roles"](message)
    bot.bot.send_message.assert_called_with(999, "Roles info")

    # /papier
    await handlers["papier"](message)
    bot.bot.send_message.assert_called_with(999, "Papier reminder")

    # /lessive
    await handlers["lessive"](message)
    bot.bot.send_message.assert_called_with(999, "Lessive info")

    # /whoishere
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

    # regexp jeremie?
    await handlers["jeremie?"](message)
    bot.bot.reply_to.assert_called_with(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")


@pytest.mark.asyncio
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_myid_handler(mock_group, mock_token):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999
    message.from_user.id = 42
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"

    await handlers["myid"](message)
    call_args = bot.bot.send_message.call_args
    assert "42" in call_args[0][1]
    assert "Test User" in call_args[0][1]


@pytest.mark.asyncio
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_unknown_user(mock_group, mock_token):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999
    message.from_user.id = 99999  # Not in TELEGRAM_USER_MAP

    await handlers["done"](message)
    call_args = bot.bot.send_message.call_args
    assert "Je ne sais pas qui tu es" in call_args[0][1]


@pytest.mark.asyncio
@patch("src.drahmbot.chores.mark_done", return_value=True)
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_success(mock_group, mock_token, mock_role, mock_mark):
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"

    try:
        bot = Drahmbot()
        bot.bot.send_message = AsyncMock()
        handlers = _capture_handlers(bot)

        message = MagicMock()
        message.chat.id = 999
        message.from_user.id = 42

        await handlers["done"](message)
        call_args = bot.bot.send_message.call_args
        assert "Bien joué" in call_args[0][1]
        assert "CUISINE" in call_args[0][1]
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.mark_done", return_value=False)
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_already_done(mock_group, mock_token, mock_role, mock_mark):
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"

    try:
        bot = Drahmbot()
        bot.bot.send_message = AsyncMock()
        handlers = _capture_handlers(bot)

        message = MagicMock()
        message.chat.id = 999
        message.from_user.id = 42

        await handlers["done"](message)
        call_args = bot.bot.send_message.call_args
        assert "déjà marqué" in call_args[0][1]
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_thursday_reminder", return_value="Rappel du jeudi : tout ok")
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_reminder_handler(mock_group, mock_token, mock_assignments, mock_reminder):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["reminder"](message)
    bot.bot.send_message.assert_called_with(999, "Rappel du jeudi : tout ok")


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_sunday_recap", return_value="Récap de la semaine")
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_recap_handler(mock_group, mock_token, mock_assignments, mock_recap):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["recap"](message)
    bot.bot.send_message.assert_called_with(999, "Récap de la semaine")


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_carton_reminder", return_value="Carton reminder")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_carton_handler(mock_group, mock_token, mock_carton):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["carton"](message)
    bot.bot.send_message.assert_called_with(999, "Carton reminder")
