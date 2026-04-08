import datetime
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.drahmbot import (
    Drahmbot, ColocAccessMiddleware, TELEGRAM_USER_MAP, colocataires,
    _build_done_keyboard, _build_done_text,
)

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
    """Re-register handlers and capture them by command name (and callback queries)."""
    handlers = {}

    def capture_message_handler(*args, **kwargs):
        def wrapper(func):
            if "commands" in kwargs:
                for cmd in kwargs["commands"]:
                    handlers[cmd] = func
            if "regexp" in kwargs:
                handlers[kwargs["regexp"]] = func
            return func
        return wrapper

    def capture_callback_handler(*args, **kwargs):
        def wrapper(func):
            handlers["_callback_query"] = func
            return func
        return wrapper

    bot.bot.message_handler = capture_message_handler
    bot.bot.callback_query_handler = capture_callback_handler
    bot.register_handlers()
    return handlers


@pytest.mark.asyncio
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
@patch("src.drahmbot.utils.is_even_week", return_value=True)
@patch("src.drahmbot.menage.getRoles", return_value="Roles info")
@patch("src.drahmbot.menage.get_papier_reminder", return_value="Papier reminder")
@patch("src.drahmbot.menage.getCarteDeLessive", return_value="Lessive info")
@patch("src.drahmbot.social.is_present_dinner", return_value="Who is here?")
async def test_bot_handlers(
    mock_who, mock_lessive, mock_papier, mock_roles, mock_even, mock_group, mock_token
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
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_sends_keyboard(
    mock_group, mock_token, mock_dt, mock_role, mock_subtasks, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
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
        assert "CUISINE" in call_args[0][1]
        assert "reply_markup" in call_args[1]
        keyboard = call_args[1]["reply_markup"]
        assert len(keyboard.keyboard) == 3  # frigo, plan de travail, rangement
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "SOLs": {"subtasks": {"aspirateur": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["aspirateur", "panosse"])
@patch("src.drahmbot.menage.get_role_for_person", return_value="SOLs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_subtask_role(
    mock_group, mock_token, mock_dt, mock_role, mock_subtasks, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Léa"

    try:
        bot = Drahmbot()
        bot.bot.send_message = AsyncMock()
        handlers = _capture_handlers(bot)

        message = MagicMock()
        message.chat.id = 999
        message.from_user.id = 42

        await handlers["done"](message)
        call_args = bot.bot.send_message.call_args
        text = call_args[0][1]
        assert "1/2" in text
        keyboard = call_args[1]["reply_markup"]
        assert len(keyboard.keyboard) == 2  # 2 subtask buttons
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


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_stats", return_value="Stats :\n  🥇 Timon : 3 tâches")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_stats_handler_dev_chat(mock_group, mock_token, mock_stats):
    bot = Drahmbot()
    bot.dev_chat_id = "-4867763410"
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = -4867763410

    await handlers["stats"](message)
    bot.bot.send_message.assert_called_once_with(-4867763410, "Stats :\n  🥇 Timon : 3 tâches")


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_stats", return_value="Stats :\n  🥇 Timon : 3 tâches")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_stats_handler_other_chat_ignored(mock_group, mock_token, mock_stats):
    bot = Drahmbot()
    bot.dev_chat_id = "-4867763410"
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = -9999999999  # Not the dev chat

    await handlers["stats"](message)
    bot.bot.send_message.assert_not_called()


# --- Biweekly papier tests ---

@pytest.mark.asyncio
@patch("src.drahmbot.utils.is_even_week", return_value=False)
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_papier_skipped_on_odd_week(mock_group, mock_token, mock_even):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["papier"](message)
    bot.bot.send_message.assert_not_called()


# --- ColocAccessMiddleware tests ---

@pytest.mark.asyncio
async def test_middleware_allows_known_user():
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    message = MagicMock()
    message.from_user.id = 891406979  # Alexis
    message.text = "/roles"
    result = await mw.pre_process(message, {})
    assert result is None


@pytest.mark.asyncio
async def test_middleware_blocks_unknown_user():
    from telebot.handler_backends import CancelUpdate
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    message = MagicMock()
    message.from_user.id = 99999999  # Not in map
    message.text = "/roles"
    result = await mw.pre_process(message, {})
    assert isinstance(result, CancelUpdate)


@pytest.mark.asyncio
async def test_middleware_allows_eventbridge():
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    message = MagicMock()
    message.from_user = None
    message.text = "/papier"
    result = await mw.pre_process(message, {})
    assert result is None


@pytest.mark.asyncio
async def test_middleware_allows_myid():
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    message = MagicMock()
    message.from_user.id = 99999999  # Unknown user
    message.text = "/myid"
    result = await mw.pre_process(message, {})
    assert result is None


@pytest.mark.asyncio
async def test_middleware_allows_known_user_callback():
    """Callback queries from known users pass through middleware."""
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    callback = MagicMock(spec=[])  # no 'text' attribute
    callback.from_user = MagicMock()
    callback.from_user.id = 891406979  # Alexis
    result = await mw.pre_process(callback, {})
    assert result is None


@pytest.mark.asyncio
async def test_middleware_blocks_unknown_user_callback():
    from telebot.handler_backends import CancelUpdate
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    callback = MagicMock(spec=[])  # no 'text' attribute
    callback.from_user = MagicMock()
    callback.from_user.id = 99999999
    result = await mw.pre_process(callback, {})
    assert isinstance(result, CancelUpdate)


# --- Keyboard builder tests ---


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=None)
def test_build_done_keyboard_simple_role(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15)
    assert len(keyboard.keyboard) == 1
    btn = keyboard.keyboard[0][0]
    assert "CUISINE" in btn.text
    assert btn.callback_data == "done:15:CUISINE"
    assert "\u2b1c" in btn.text  # not done


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=None)
def test_build_done_keyboard_simple_done(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15)
    btn = keyboard.keyboard[0][0]
    assert "\u2705" in btn.text


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["aspirateur", "panosse"])
def test_build_done_keyboard_subtask_role(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("SOLs", 15)
    assert len(keyboard.keyboard) == 2
    assert "aspirateur" in keyboard.keyboard[0][0].text
    assert "panosse" in keyboard.keyboard[1][0].text
    assert keyboard.keyboard[0][0].callback_data == "done:15:SOLs:aspirateur"


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=None)
def test_build_done_text_simple_not_done(mock_subtasks, mock_status):
    text = _build_done_text("CUISINE", "Timon")
    assert "CUISINE" in text
    assert "Timon" in text
    assert "clique" in text


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=None)
def test_build_done_text_simple_done(mock_subtasks, mock_status):
    text = _build_done_text("CUISINE", "Timon")
    assert "fait" in text
    assert "\u2705" in text


@patch("src.drahmbot.chores.get_week_status", return_value={
    "SOLs": {"subtasks": {"aspirateur": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["aspirateur", "panosse"])
def test_build_done_text_subtask_partial(mock_subtasks, mock_status):
    text = _build_done_text("SOLs", "Léa")
    assert "1/2" in text


# --- Callback handler tests ---


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"by": "Timon", "at": "..."},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=None)
@patch("src.drahmbot.chores.toggle_role", return_value=False)
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_callback_toggle_role(
    mock_group, mock_token, mock_dt, mock_role, mock_toggle,
    mock_subtasks, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "done:15:CUISINE"
        call.from_user.id = 42
        call.id = "cb1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("CUISINE", "Timon")
        bot.bot.edit_message_text.assert_called_once()
        bot.bot.answer_callback_query.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "annulé" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["aspirateur", "panosse"])
@patch("src.drahmbot.chores.toggle_subtask", return_value=True)
@patch("src.drahmbot.menage.get_role_for_person", return_value="SOLs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_callback_toggle_subtask(
    mock_group, mock_token, mock_dt, mock_role, mock_toggle,
    mock_subtasks, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Léa"

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "done:15:SOLs:aspirateur"
        call.from_user.id = 42
        call.id = "cb2"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("SOLs", "aspirateur", "Léa")
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "aspirateur fait" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_callback_stale_week(mock_group, mock_token, mock_dt):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "done:15:CUISINE"  # week 15, but current is 16
    call.from_user.id = 891406979
    call.id = "cb3"

    await handlers["_callback_query"](call)
    toast = bot.bot.answer_callback_query.call_args
    assert "terminée" in toast[0][1]


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_role_for_person", return_value="SDBs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_callback_wrong_user(mock_group, mock_token, mock_dt, mock_role):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Maël"

    try:
        bot = Drahmbot()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "done:15:CUISINE"  # Maël is assigned SDBs, not CUISINE
        call.from_user.id = 42
        call.id = "cb4"

        await handlers["_callback_query"](call)
        toast = bot.bot.answer_callback_query.call_args
        assert "pas ta tâche" in toast[0][1]
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)
