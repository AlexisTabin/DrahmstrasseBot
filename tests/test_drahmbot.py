import datetime
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.drahmbot import (
    Drahmbot, ColocAccessMiddleware, TELEGRAM_USER_MAP, colocataires, COMMANDS,
    _build_done_keyboard, _build_done_text,
    _build_plants_keyboard, _build_plants_text,
    _build_dechets_keyboard, _build_dechets_text,
    _build_subtask_keyboard, _build_subtask_text,
    _build_cendrier_keyboard, _build_cendrier_text,
    _build_chiffons_keyboard, _build_chiffons_text,
    _build_counter_keyboard, _build_counter_text,
    _build_commands_text,
)
from src import menage

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
        func_filter = kwargs.get("func")

        def wrapper(handler_fn):
            pairs = handlers.setdefault("_callback_pairs", [])
            pairs.append((func_filter, handler_fn))

            async def dispatcher(call):
                for filt, h in handlers["_callback_pairs"]:
                    if filt is None or filt(call):
                        return await h(call)

            handlers["_callback_query"] = dispatcher
            return handler_fn
        return wrapper

    bot.bot.message_handler = capture_message_handler
    bot.bot.callback_query_handler = capture_callback_handler
    bot.register_handlers()
    return handlers


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
@patch("src.drahmbot.utils.is_even_week", return_value=True)
@patch("src.drahmbot.menage.getRoles", return_value="Roles info")
@patch("src.drahmbot.menage.get_papier_reminder", return_value="Papier reminder")
@patch("src.drahmbot.menage.getCarteDeLessive", return_value="Lessive info")
@patch("src.drahmbot.social.is_present_dinner", return_value="Who is here?")
async def test_bot_handlers(
    mock_who, mock_lessive, mock_papier, mock_roles, mock_even,
    mock_group, mock_token, mock_status,
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

    # /papier — now sends with reply_markup
    await handlers["papier"](message)
    papier_call = bot.bot.send_message.call_args
    assert papier_call[0][0] == 999
    assert papier_call[0][1] == "Papier reminder"
    assert "reply_markup" in papier_call[1]

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
async def test_commands_handler_sends_commands_list(mock_group, mock_token):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["commands"](message)
    call_args = bot.bot.send_message.call_args
    assert call_args[0][0] == 999
    assert "/recap" in call_args[0][1]
    assert "/frigo" in call_args[0][1]


def test_build_commands_text_lists_every_documented_command_and_subtask():
    result = _build_commands_text()
    lines = result.split("\n")
    for cmd, _description in COMMANDS:
        assert any(line.startswith(f"/{cmd} :") for line in lines)
    # Whole-token match, not `in result`: a couple of subtask names are
    # prefixes of each other (e.g. "poubelle" of "poubelles"), so a plain
    # substring check wouldn't notice one going missing while the other stays.
    # A line may carry an "(optionnel, compteur)" annotation after the command.
    for cmd in menage.SUBTASK_COMMANDS:
        assert any(
            line == f"/{cmd}" or line.startswith(f"/{cmd} (") for line in lines
        ), f"/{cmd} missing from the subtask list"


@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
def test_commands_list_matches_registered_handlers(mock_group, mock_token):
    """Guards against drift: any command registered via @self.bot.message_handler(commands=[...]) must either be listed in COMMANDS, be one of the auto-derived subtask shortcuts, or be explicitly excluded (only /stats: dev-chat only, deliberately not advertised in the group-facing /commands). Add a new command without updating COMMANDS and this test fails instead of /commands silently going stale. Uses _capture_handlers (the same public commands=[...] kwarg every other test in this file relies on) instead of reaching into telebot's private message_handlers/filters internals, and mocks the token/chat_id so it doesn't depend on some other test having already constructed the Drahmbot singleton first."""
    bot = Drahmbot()
    handlers = _capture_handlers(bot)
    non_commands = {"_callback_pairs", "_callback_query", "jeremie?"}
    registered = set(handlers.keys()) - non_commands

    documented = {cmd for cmd, _description in COMMANDS}
    subtask_commands = set(menage.SUBTASK_COMMANDS.keys())
    deliberately_excluded = {"stats"}

    undocumented = registered - documented - subtask_commands - deliberately_excluded
    assert undocumented == set(), (
        f"{undocumented} registered but missing from drahmbot.COMMANDS"
    )


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
@patch("src.drahmbot.cendrier.get_week_state", return_value={})
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_mael_gets_cendrier_in_same_message(
    mock_group, mock_token, mock_dt, mock_role, mock_subtasks, mock_status, mock_cendrier_state,
):
    """Cendrier is standalone (never part of role rotation), but /done still
    folds it into Maël's single message rather than a second one."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Maël"

    try:
        bot = Drahmbot()
        bot.bot.send_message = AsyncMock()
        handlers = _capture_handlers(bot)

        message = MagicMock()
        message.chat.id = 999
        message.from_user.id = 42

        await handlers["done"](message)
        assert bot.bot.send_message.call_count == 1
        call_args = bot.bot.send_message.call_args
        assert "Cendrier" in call_args[0][1]
        keyboard = call_args[1]["reply_markup"]
        assert keyboard.keyboard[-1][0].callback_data == "donecendrier:15:CUISINE"
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_handler_non_smoker_no_cendrier(
    mock_group, mock_token, mock_dt, mock_role, mock_subtasks, mock_status,
):
    """Only smokers (currently just Maël) get the extra cendrier row/line."""
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
        assert bot.bot.send_message.call_count == 1
        call_args = bot.bot.send_message.call_args
        assert "Cendrier" not in call_args[0][1]
        keyboard = call_args[1]["reply_markup"]
        assert not any(
            btn.callback_data.startswith("donecendrier:")
            for row in keyboard.keyboard for btn in row
        )
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
@patch("src.drahmbot.chores.get_leaderboard", return_value="Palmarès de la coloc")
@patch("src.drahmbot.chores.get_sunday_recap", return_value="Récap de la semaine")
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_recap_handler(mock_group, mock_token, mock_assignments, mock_recap, mock_leaderboard):
    """/recap also sends the all-time leaderboard as a second message."""
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["recap"](message)
    assert bot.bot.send_message.call_args_list == [
        ((999, "Récap de la semaine"),),
        ((999, "Palmarès de la coloc"),),
    ]


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_leaderboard", return_value="Palmarès de la coloc")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_leaderboard_handler_any_chat(mock_group, mock_token, mock_leaderboard):
    """/leaderboard is public: unlike /stats it's not gated to the dev chat."""
    bot = Drahmbot()
    bot.dev_chat_id = "-4867763410"
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = -9999999999  # not the dev chat

    await handlers["leaderboard"](message)
    bot.bot.send_message.assert_called_once_with(-9999999999, "Palmarès de la coloc")


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_carton_reminder", return_value="Carton reminder")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_carton_handler(mock_group, mock_token, mock_carton, mock_status):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["carton"](message)
    call_args = bot.bot.send_message.call_args
    assert call_args[0][0] == 999
    assert call_args[0][1] == "Carton reminder"
    assert "reply_markup" in call_args[1]


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
async def test_middleware_allows_commands_for_unonboarded_users():
    """A not-yet-onboarded roommate must be able to run /commands to
    discover /myid exists in the first place."""
    mw = ColocAccessMiddleware(TELEGRAM_USER_MAP)
    message = MagicMock()
    message.from_user.id = 99999999  # Unknown user
    message.text = "/commands"
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
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_keyboard_cuisine_not_done(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15, "Timon")
    assert len(keyboard.keyboard) == 3
    assert "frigo" in keyboard.keyboard[0][0].text
    assert "plan de travail" in keyboard.keyboard[1][0].text
    assert "rangement" in keyboard.keyboard[2][0].text
    assert keyboard.keyboard[0][0].callback_data == "done:15:CUISINE:frigo"
    assert "\u2b1c" in keyboard.keyboard[0][0].text  # not done


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "frigo": {"by": "Timon", "at": "..."},
        "plan de travail": {"by": "Timon", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
    }},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_keyboard_cuisine_done(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15, "Timon")
    assert len(keyboard.keyboard) == 3
    assert "\u2705" in keyboard.keyboard[0][0].text


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["aspirateur", "panosse"])
def test_build_done_keyboard_subtask_role(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("SOLs", 15, "Léa")
    assert len(keyboard.keyboard) == 2
    assert "aspirateur" in keyboard.keyboard[0][0].text
    assert "panosse" in keyboard.keyboard[1][0].text
    assert keyboard.keyboard[0][0].callback_data == "done:15:SOLs:aspirateur"


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail"])
def test_build_done_keyboard_counter_subtask_shows_count_zero(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15, "Timon")
    assert "plan de travail" in keyboard.keyboard[1][0].text
    assert "(0x)" in keyboard.keyboard[1][0].text
    assert "⬜" in keyboard.keyboard[1][0].text
    # Same "done:" callback prefix as any other subtask, just branched on server-side
    assert keyboard.keyboard[1][0].callback_data == "done:15:CUISINE:plan de travail"


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"plan de travail": {"count": 3, "by": "Timon", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail"])
def test_build_done_keyboard_counter_subtask_shows_positive_count(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15, "Timon")
    assert "(3x)" in keyboard.keyboard[1][0].text
    assert "✅" in keyboard.keyboard[1][0].text


@patch("src.drahmbot.cendrier.get_week_state", return_value={})
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_keyboard_smoker_gets_cendrier_row(mock_subtasks, mock_status, mock_cendrier_state):
    keyboard = _build_done_keyboard("CUISINE", 15, "Maël")
    assert len(keyboard.keyboard) == 4  # 3 subtasks + cendrier
    assert keyboard.keyboard[3][0].callback_data == "donecendrier:15:CUISINE"
    assert "Cendrier" in keyboard.keyboard[3][0].text
    assert "⬜" in keyboard.keyboard[3][0].text


@patch("src.drahmbot.cendrier.get_week_state", return_value={"by": "Maël", "at": "..."})
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_keyboard_smoker_cendrier_row_reflects_done(
    mock_subtasks, mock_status, mock_cendrier_state,
):
    keyboard = _build_done_keyboard("CUISINE", 15, "Maël")
    assert "✅" in keyboard.keyboard[3][0].text


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_keyboard_non_smoker_has_no_cendrier_row(mock_subtasks, mock_status):
    keyboard = _build_done_keyboard("CUISINE", 15, "Timon")
    assert len(keyboard.keyboard) == 3
    assert not any(
        btn.callback_data.startswith("donecendrier:")
        for row in keyboard.keyboard for btn in row
    )


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_text_cuisine_not_done(mock_subtasks, mock_status):
    text = _build_done_text("CUISINE", "Timon")
    assert "CUISINE" in text
    assert "Timon" in text
    assert "0/3" in text


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "frigo": {"by": "Timon", "at": "..."},
        "plan de travail": {"by": "Timon", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
    }},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_text_cuisine_done(mock_subtasks, mock_status):
    text = _build_done_text("CUISINE", "Timon")
    assert "3/3" in text
    assert "\u2705" in text


@patch("src.drahmbot.chores.get_week_status", return_value={
    "SOLs": {"subtasks": {"aspirateur": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["aspirateur", "panosse"])
def test_build_done_text_subtask_partial(mock_subtasks, mock_status):
    text = _build_done_text("SOLs", "Léa")
    assert "1/2" in text


@patch("src.drahmbot.cendrier.get_week_state", return_value={})
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_text_smoker_appends_cendrier_line(mock_subtasks, mock_status, mock_cendrier_state):
    text = _build_done_text("CUISINE", "Maël")
    assert "0/3" in text
    assert "Cendrier" in text


@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
def test_build_done_text_non_smoker_has_no_cendrier_line(mock_subtasks, mock_status):
    text = _build_done_text("CUISINE", "Timon")
    assert "Cendrier" not in text


# --- Callback handler tests ---


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"frigo": {"by": "Timon", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.chores.toggle_subtask", return_value=False)
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_callback_toggle_cuisine_subtask(
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
        call.data = "done:15:CUISINE:frigo"
        call.from_user.id = 42
        call.id = "cb1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("CUISINE", "frigo", "Timon")
        bot.bot.edit_message_text.assert_called_once()
        bot.bot.answer_callback_query.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "frigo annulé" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"plan de travail": {"count": 2, "by": "Timon", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail"])
@patch("src.drahmbot.chores.increment_subtask_counter",
       return_value={"count": 3, "counts": {"Timon": 3}})
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.menage.get_role_for_person", return_value="CUISINE")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_callback_done_increments_counter_subtask(
    mock_group, mock_token, mock_dt, mock_role, mock_toggle, mock_increment,
    mock_subtasks, mock_status,
):
    """Pressing a counter subtask's button from /done increments instead of toggling."""
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
        call.data = "done:15:CUISINE:plan de travail"
        call.from_user.id = 42
        call.id = "cb-counter-1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_increment.assert_called_once_with("CUISINE", "plan de travail", "Timon")
        mock_toggle.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "3x" in toast
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


# --- /arrosage tests ---


def test_build_plants_keyboard_unwatered():
    kb = _build_plants_keyboard("2026-06-01", False)
    assert len(kb.keyboard) == 1
    assert "⬜" in kb.keyboard[0][0].text
    assert kb.keyboard[0][0].callback_data == "plants:2026-06-01"


def test_build_plants_keyboard_watered():
    kb = _build_plants_keyboard("2026-06-01", True)
    assert len(kb.keyboard) == 1
    assert "✅" in kb.keyboard[0][0].text


def test_build_plants_text_no_vote():
    text = _build_plants_text("2026-06-01", 28.0, {})
    assert "28" in text  # rounded temp present


def test_build_plants_text_header_stable_across_calls():
    a = _build_plants_text("2026-06-01", 28.0, {})
    b = _build_plants_text("2026-06-01", 28.0, {})
    assert a == b


def test_build_plants_text_with_watered_vote():
    text = _build_plants_text(
        "2026-06-01", 28.0,
        {"state": "watered", "by": "Léa", "at": "..."},
    )
    assert "Léa" in text
    assert "arrosé" in text


def test_build_plants_text_with_legacy_needs_vote():
    """Pre-revision rows still render as 'watered' messages."""
    text = _build_plants_text(
        "2026-06-01", 28.0,
        {"state": "needs", "by": "Timon", "at": "..."},
    )
    assert "Timon" in text
    assert "arrosé" in text


@pytest.mark.asyncio
@patch("src.drahmbot.plants.get_today_state", return_value={})
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=28.4)
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_hot_day_sends_message(
    mock_group, mock_token, mock_temp, mock_state,
):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_called_once()
    call_args = bot.bot.send_message.call_args
    assert call_args[0][0] == 999
    assert "reply_markup" in call_args[1]
    kb = call_args[1]["reply_markup"]
    assert len(kb.keyboard) == 1


@pytest.mark.asyncio
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=18.0)
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_cool_day_silent(mock_group, mock_token, mock_temp):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=None)
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_weather_unavailable_silent(mock_group, mock_token, mock_temp):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("src.drahmbot.plants.get_today_state", return_value={})
@patch("src.drahmbot.plants.get_last_watered_date", return_value=None)
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=22.0)
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_warm_day_no_history_reminds(
    mock_group, mock_token, mock_temp, mock_last, mock_state,
):
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_called_once()


@pytest.mark.asyncio
@patch("src.drahmbot.plants.get_last_watered_date")
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=22.0)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_warm_day_recent_water_silent(
    mock_group, mock_token, mock_dt, mock_temp, mock_last,
):
    today = datetime.date(2026, 6, 3)
    mock_dt.date.today.return_value = today
    mock_last.return_value = today  # watered today

    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("src.drahmbot.plants.get_last_watered_date")
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=22.0)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_warm_day_yesterday_water_silent(
    mock_group, mock_token, mock_dt, mock_temp, mock_last,
):
    today = datetime.date(2026, 6, 3)
    mock_dt.date.today.return_value = today
    mock_last.return_value = today - datetime.timedelta(days=1)  # 1 day < cooldown

    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("src.drahmbot.plants.get_today_state", return_value={})
@patch("src.drahmbot.plants.get_last_watered_date")
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=22.0)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_arrosage_warm_day_old_water_reminds(
    mock_group, mock_token, mock_dt, mock_temp, mock_last, mock_state,
):
    today = datetime.date(2026, 6, 3)
    mock_dt.date.today.return_value = today
    mock_last.return_value = today - datetime.timedelta(days=2)  # cooldown met

    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["arrosage"](message)
    bot.bot.send_message.assert_called_once()


@pytest.mark.asyncio
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=29.0)
@patch("src.drahmbot.plants.toggle_today_state",
       return_value={"state": "watered", "by": "Léa", "at": "..."})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_plants_callback_marks_watered(
    mock_group, mock_token, mock_dt, mock_toggle, mock_temp,
):
    mock_dt.date.today.return_value.isoformat.return_value = "2026-06-01"
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Léa"

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "plants:2026-06-01"
        call.from_user.id = 42
        call.id = "cbp1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("Léa")
        bot.bot.edit_message_text.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "noté" in toast.lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=29.0)
@patch("src.drahmbot.plants.toggle_today_state", return_value={})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_plants_callback_unmarks_when_already_watered(
    mock_group, mock_token, mock_dt, mock_toggle, mock_temp,
):
    """Re-clicking the button clears the watered mark (toggle off)."""
    mock_dt.date.today.return_value.isoformat.return_value = "2026-06-01"
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "plants:2026-06-01"
        call.from_user.id = 42
        call.id = "cbp2"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("Timon")
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "annulé" in toast.lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.plants.toggle_today_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_plants_callback_stale_date(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isoformat.return_value = "2026-06-02"

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    bot.bot.edit_message_text = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "plants:2026-06-01"  # yesterday's vote
    call.from_user.id = 891406979
    call.id = "cbp3"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args
    assert "Trop tard" in toast[0][1]


@pytest.mark.asyncio
@patch("src.drahmbot.plants.toggle_today_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_plants_callback_unknown_user(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isoformat.return_value = "2026-06-01"

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "plants:2026-06-01"
    call.from_user.id = 99999  # not in TELEGRAM_USER_MAP
    call.id = "cbp4"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args
    assert "reconnu" in toast[0][1]


@pytest.mark.asyncio
@patch("src.drahmbot.plants.toggle_today_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_plants_callback_malformed_data(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isoformat.return_value = "2026-06-01"

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "plants:2026-06-01:extra"  # too many parts for the new format
    call.from_user.id = 891406979
    call.id = "cbp5"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args
    assert "invalides" in toast[0][1].lower()


# --- Dechets (papier/carton done-button) keyboard/text helpers ---


def test_build_dechets_keyboard_unchecked():
    kb = _build_dechets_keyboard(15, "carton", {})
    assert len(kb.keyboard) == 1
    button = kb.keyboard[0][0]
    assert "⬜" in button.text
    assert "carton" in button.text
    assert button.callback_data == "dechets:15:carton"


def test_build_dechets_keyboard_checked():
    role_data = {"subtasks": {"carton": {"by": "Timon", "at": "..."}}}
    kb = _build_dechets_keyboard(15, "carton", role_data)
    button = kb.keyboard[0][0]
    assert "✅" in button.text


def test_build_dechets_keyboard_only_reflects_own_subtask():
    """A papier-done state must not flip the carton keyboard to checked."""
    role_data = {"subtasks": {"papier": {"by": "Timon", "at": "..."}}}
    kb = _build_dechets_keyboard(15, "carton", role_data)
    assert "⬜" in kb.keyboard[0][0].text


def test_build_dechets_keyboard_papier_callback_data():
    kb = _build_dechets_keyboard(20, "papier", {})
    assert kb.keyboard[0][0].callback_data == "dechets:20:papier"


def test_build_dechets_text_no_doer():
    text = _build_dechets_text("Timon doit sortir le carton mercredi", "carton", {})
    assert text == "Timon doit sortir le carton mercredi"


def test_build_dechets_text_with_doer():
    role_data = {"subtasks": {"carton": {"by": "Léa", "at": "..."}}}
    text = _build_dechets_text(
        "Timon doit sortir le carton mercredi", "carton", role_data,
    )
    assert "Timon doit sortir le carton mercredi" in text
    assert "Léa" in text
    assert "carton" in text
    assert "✅" in text


def test_build_dechets_text_other_subtask_done_does_not_pollute():
    """If only papier is marked, the carton message stays clean."""
    role_data = {"subtasks": {"papier": {"by": "Léa", "at": "..."}}}
    text = _build_dechets_text(
        "Timon doit sortir le carton mercredi", "carton", role_data,
    )
    assert text == "Timon doit sortir le carton mercredi"


# --- /papier and /carton: keyboard attachment ---


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_papier_reminder",
       return_value="Timon doit sortir le papier lundi")
@patch("src.drahmbot.utils.is_even_week", return_value=True)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_papier_handler_attaches_keyboard(
    mock_group, mock_token, mock_dt, mock_even, mock_papier, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["papier"](message)
    bot.bot.send_message.assert_called_once()
    call_args = bot.bot.send_message.call_args
    assert call_args[0][0] == 999
    assert "papier" in call_args[0][1].lower()
    assert "reply_markup" in call_args[1]
    kb = call_args[1]["reply_markup"]
    assert len(kb.keyboard) == 1
    assert kb.keyboard[0][0].callback_data == "dechets:15:papier"


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "DÉCHETS": {"subtasks": {"papier": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_papier_reminder",
       return_value="Timon doit sortir le papier lundi")
@patch("src.drahmbot.utils.is_even_week", return_value=True)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_papier_handler_reflects_existing_done_state(
    mock_group, mock_token, mock_dt, mock_even, mock_papier, mock_status,
):
    """If papier was already marked, /papier shows the doer + checked button."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["papier"](message)
    call_args = bot.bot.send_message.call_args
    text = call_args[0][1]
    assert "Léa" in text
    kb = call_args[1]["reply_markup"]
    assert "✅" in kb.keyboard[0][0].text


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_carton_reminder",
       return_value="Timon doit sortir le carton mercredi")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_carton_handler_attaches_keyboard(
    mock_group, mock_token, mock_dt, mock_carton, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["carton"](message)
    call_args = bot.bot.send_message.call_args
    assert "carton" in call_args[0][1].lower()
    kb = call_args[1]["reply_markup"]
    assert kb.keyboard[0][0].callback_data == "dechets:15:carton"


# --- Dechets callback handler tests ---


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_papier_reminder",
       return_value="Timon doit sortir le papier lundi")
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["poubelle", "carton", "compost", "verre", "plastique", "papier"])
@patch("src.drahmbot.chores.toggle_subtask", return_value=True)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_open_click_anyone_can_mark(
    mock_group, mock_token, mock_dt, mock_toggle, mock_subtasks, mock_status, mock_papier,
):
    """Anyone in the coloc can mark papier/carton as done, even if they're not
    the assigned DÉCHETS person."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Léa"  # not the assigned person

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "dechets:15:papier"
        call.from_user.id = 42
        call.id = "cbd1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("DÉCHETS", "papier", "Léa")
        bot.bot.edit_message_text.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "papier" in toast.lower()
        assert "fait" in toast.lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_carton_reminder",
       return_value="Timon doit sortir le carton mercredi")
@patch("src.drahmbot.chores.get_week_status", return_value={
    "DÉCHETS": {"subtasks": {"carton": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["poubelle", "carton", "compost", "verre", "plastique"])
@patch("src.drahmbot.chores.toggle_subtask", return_value=False)
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_doer_can_undo(
    mock_group, mock_token, mock_dt, mock_toggle, mock_subtasks, mock_status, mock_carton,
):
    """The original doer can untoggle their own mark."""
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
        call.data = "dechets:15:carton"
        call.from_user.id = 42
        call.id = "cbd2"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("DÉCHETS", "carton", "Léa")
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "annul" in toast.lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "DÉCHETS": {"subtasks": {"carton": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["poubelle", "carton", "compost", "verre", "plastique"])
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_non_doer_cannot_undo(
    mock_group, mock_token, mock_dt, mock_toggle, mock_subtasks, mock_status,
):
    """A different coloc cannot untoggle someone else's mark. The doer's name is
    surfaced in the toast so people know who to ask."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"  # not Léa

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "dechets:15:carton"
        call.from_user.id = 42
        call.id = "cbd3"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "Léa" in toast  # doer's name mentioned
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_stale_week(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "dechets:15:carton"  # last week
    call.from_user.id = 891406979
    call.id = "cbd4"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "semaine" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_unknown_user(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "dechets:15:carton"
    call.from_user.id = 99999  # not in TELEGRAM_USER_MAP
    call.id = "cbd5"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "reconnu" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_malformed_data(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "dechets:15"  # missing subtask part
    call.from_user.id = 891406979
    call.id = "cbd6"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["poubelle", "carton", "compost"])  # papier NOT included (odd week)
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_dechets_callback_invalid_subtask(
    mock_group, mock_token, mock_dt, mock_toggle, mock_subtasks,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "dechets:15:papier"  # papier not a subtask this week
    call.from_user.id = 891406979
    call.id = "cbd7"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "inconnue" in toast.lower()


# --- Generic per-subtask commands (e.g. /frigo) ---


def test_build_subtask_keyboard_unchecked():
    kb = _build_subtask_keyboard(15, "frigo", False)
    assert len(kb.keyboard) == 1
    assert "⬜" in kb.keyboard[0][0].text
    assert kb.keyboard[0][0].callback_data == "subtask:15:frigo"


def test_build_subtask_keyboard_checked():
    kb = _build_subtask_keyboard(15, "frigo", True)
    assert "✅" in kb.keyboard[0][0].text


def test_build_subtask_text_not_done():
    text = _build_subtask_text("CUISINE", "frigo", "Timon", None)
    assert "frigo" in text
    assert "Timon" in text
    assert "clique pour marquer" in text


def test_build_subtask_text_done_by_assigned_person():
    text = _build_subtask_text(
        "CUISINE", "frigo", "Timon", {"by": "Timon", "at": "..."},
    )
    assert "fait par Timon" in text
    assert "✅" in text


def test_build_subtask_text_done_by_someone_else():
    """The whole point: another roommate did the fridge for Timon."""
    text = _build_subtask_text(
        "CUISINE", "frigo", "Timon", {"by": "Léa", "at": "..."},
    )
    assert "fait par Léa" in text
    assert "Timon" in text  # names whose task it was
    assert "✅" in text


# --- Counter subtask builder tests (/plandetravail) ---


def test_build_counter_keyboard_shows_count_and_callback():
    kb = _build_counter_keyboard(15, "plandetravail", 2)
    assert "2" in kb.keyboard[0][0].text
    assert kb.keyboard[0][0].callback_data == "counter:15:plandetravail"


def test_build_counter_keyboard_at_zero_has_no_reset_button():
    kb = _build_counter_keyboard(15, "plandetravail", 0)
    assert len(kb.keyboard) == 1


def test_build_counter_keyboard_positive_count_adds_reset_button():
    kb = _build_counter_keyboard(15, "plandetravail", 2)
    assert len(kb.keyboard) == 2
    assert kb.keyboard[1][0].callback_data == "resetcounter:15:plandetravail"


def test_build_counter_text_zero():
    text = _build_counter_text("CUISINE", "plan de travail", "Timon", 0)
    assert "plan de travail" in text
    assert "Timon" in text
    assert "clique" in text


def test_build_counter_text_positive():
    text = _build_counter_text("CUISINE", "plan de travail", "Timon", 4)
    assert "4x" in text
    assert "✅" in text


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_command_sends_keyboard(
    mock_group, mock_token, mock_dt, mock_assignments, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["frigo"](message)
    call_args = bot.bot.send_message.call_args
    assert call_args[0][0] == 999
    assert "frigo" in call_args[0][1]
    assert "Timon" in call_args[0][1]
    assert "reply_markup" in call_args[1]
    assert call_args[1]["reply_markup"].keyboard[0][0].callback_data == "subtask:15:frigo"


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"frigo": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_command_reflects_existing_done_state(
    mock_group, mock_token, mock_dt, mock_assignments, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["frigo"](message)
    text = bot.bot.send_message.call_args[0][1]
    assert "Léa" in text
    kb = bot.bot.send_message.call_args[1]["reply_markup"]
    assert "✅" in kb.keyboard[0][0].text


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.chores.toggle_subtask", return_value=True)
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_anyone_can_mark(
    mock_group, mock_token, mock_dt, mock_assignments, mock_toggle, mock_subtasks, mock_status,
):
    """Léa can mark /frigo done even though the CUISINE role is Timon's this week."""
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
        call.data = "subtask:15:frigo"
        call.from_user.id = 42
        call.id = "cbs1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("CUISINE", "frigo", "Léa")
        bot.bot.edit_message_text.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "frigo fait" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"frigo": {"by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_non_doer_cannot_undo(
    mock_group, mock_token, mock_dt, mock_toggle, mock_subtasks, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"  # not Léa, who did it

    try:
        bot = Drahmbot()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "subtask:15:frigo"
        call.from_user.id = 42
        call.id = "cbs2"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "Léa" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_stale_week(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:15:frigo"
    call.from_user.id = 891406979
    call.id = "cbs3"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "semaine" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_unknown_user(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:15:frigo"
    call.from_user.id = 99999  # not in TELEGRAM_USER_MAP
    call.id = "cbs4"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "reconnu" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_malformed_data(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:15"  # missing command part
    call.from_user.id = 891406979
    call.id = "cbs5"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_non_numeric_week(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:abc:frigo"  # week number isn't an int
    call.from_user.id = 891406979
    call.id = "cbs8"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_unknown_command(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:15:nope"  # not a real subtask command
    call.from_user.id = 891406979
    call.id = "cbs6"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "inconnue" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["plan de travail", "rangement"])
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_subtask_callback_invalid_subtask_for_role(
    mock_group, mock_token, mock_dt, mock_toggle, mock_subtasks,
):
    """Defends against a stale config where the subtask was removed from the role."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:15:frigo"  # frigo no longer a valid CUISINE subtask
    call.from_user.id = 891406979
    call.id = "cbs7"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "inconnue" in toast.lower()


# --- /plandetravail: counter subtask command + callback ---


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"plan de travail": {"count": 2, "by": "Léa", "at": "..."}}},
})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_plandetravail_command_sends_counter_keyboard(
    mock_group, mock_token, mock_dt, mock_assignments, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["plandetravail"](message)
    call_args = bot.bot.send_message.call_args
    text = call_args[0][1]
    assert "2x" in text
    keyboard = call_args[1]["reply_markup"]
    assert keyboard.keyboard[0][0].callback_data == "counter:15:plandetravail"


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role",
       return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.chores.increment_subtask_counter",
       return_value={"count": 1, "counts": {"Léa": 1}})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_anyone_can_increment(
    mock_group, mock_token, mock_dt, mock_assignments, mock_increment, mock_subtasks, mock_status,
):
    """Léa can increment /plandetravail even though CUISINE is Timon's this week."""
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
        call.data = "counter:15:plandetravail"
        call.from_user.id = 42
        call.id = "cbc1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_increment.assert_called_once_with("CUISINE", "plan de travail", "Léa")
        bot.bot.edit_message_text.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "1x" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_stale_week(mock_group, mock_token, mock_dt, mock_increment):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:15:plandetravail"
    call.from_user.id = 891406979
    call.id = "cbc2"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "semaine" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_unknown_user(mock_group, mock_token, mock_dt, mock_increment):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:15:plandetravail"
    call.from_user.id = 99999  # not in TELEGRAM_USER_MAP
    call.id = "cbc3"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "reconnu" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_malformed_data(mock_group, mock_token, mock_dt, mock_increment):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:15"  # missing command part
    call.from_user.id = 891406979
    call.id = "cbc4"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_non_numeric_week(mock_group, mock_token, mock_dt, mock_increment):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:abc:plandetravail"  # week number isn't an int
    call.from_user.id = 891406979
    call.id = "cbc5"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_unknown_command(mock_group, mock_token, mock_dt, mock_increment):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:15:nope"  # not a real subtask command
    call.from_user.id = 891406979
    call.id = "cbc6"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "inconnue" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["rangement"])
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_invalid_subtask_for_role(
    mock_group, mock_token, mock_dt, mock_increment, mock_subtasks,
):
    """Defends against a stale config where the subtask was removed from the role."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:15:plandetravail"  # plan de travail no longer a valid CUISINE subtask
    call.from_user.id = 891406979
    call.id = "cbc7"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "inconnue" in toast.lower()


# --- resetcounter: callback ---


@pytest.mark.asyncio
@patch("src.drahmbot.chores.reset_subtask_counter",
       return_value=(2, {"count": 3, "counts": {"Timon": 3}}))
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_reset_counter_callback_only_drops_the_callers_presses(
    mock_group, mock_token, mock_dt, mock_assignments, mock_reset,
):
    """Léa resets her own 2 presses on /plandetravail; Timon's 3 stay, and the
    re-rendered message shows the remaining total and breakdown."""
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
        call.data = "resetcounter:15:plandetravail"
        call.from_user.id = 42
        call.id = "cbr1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_reset.assert_called_once_with("CUISINE", "plan de travail", "Léa")
        text = bot.bot.edit_message_text.call_args[0][0]
        assert "3x" in text
        assert "Timon 3x" in text
        assert "Léa" not in text
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "2x retiré(s) de ton compteur." == toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.reset_subtask_counter",
       return_value=(0, {"count": 3, "counts": {"Timon": 3}}))
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_reset_counter_callback_says_so_when_you_have_nothing_to_reset(
    mock_group, mock_token, mock_dt, mock_reset,
):
    """The button is shared by everyone who sees the message, so it can be
    tapped by someone who never pressed +1: leave the message untouched."""
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
        call.data = "resetcounter:15:plandetravail"
        call.from_user.id = 42
        call.id = "cbr1b"

        await handlers["_callback_query"](call)
        bot.bot.edit_message_text.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "rien à remettre à 0" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.reset_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_reset_counter_callback_stale_week(mock_group, mock_token, mock_dt, mock_reset):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "resetcounter:15:plandetravail"
    call.from_user.id = 891406979
    call.id = "cbr2"

    await handlers["_callback_query"](call)
    mock_reset.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "semaine" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo"])
@patch("src.drahmbot.chores.reset_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_reset_counter_callback_rejects_subtask_no_longer_a_counter(
    mock_group, mock_token, mock_dt, mock_reset, mock_subtasks,
):
    """A "resetcounter:...:frigo" callback must not reset frigo's (non-counter) data."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "resetcounter:15:frigo"
    call.from_user.id = 891406979
    call.id = "cbr3"

    await handlers["_callback_query"](call)
    mock_reset.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "changé" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chores.increment_subtask_counter",
       return_value={"count": 1, "counts": {"Léa": 1}})
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_stale_subtask_callback_for_counter_subtask_increments_instead_of_toggling(
    mock_group, mock_token, mock_dt, mock_toggle, mock_increment,
):
    """Regression: a /plandetravail button rendered before "plan de travail"
    became a counter subtask still carries "subtask:...:plandetravail"
    callback_data (Telegram messages don't expire). Clicking it must not
    call toggle_subtask against what's now counter-shaped data."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.edit_message_text = AsyncMock()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "subtask:15:plandetravail"  # stale prefix for a now-counter subtask
    call.from_user.id = 891406979
    call.id = "cb-stale-1"
    call.message.chat.id = 999
    call.message.message_id = 100

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    mock_increment.assert_called_once_with("CUISINE", "plan de travail", "Alexis")
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "1x" in toast


@pytest.mark.asyncio
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo"])
@patch("src.drahmbot.chores.increment_subtask_counter")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_counter_callback_rejects_subtask_no_longer_a_counter(
    mock_group, mock_token, mock_dt, mock_increment, mock_subtasks,
):
    """Symmetric defense: a "counter:...:frigo" callback (frigo isn't in
    COUNTER_SUBTASKS) must not be allowed to increment frigo's data."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "counter:15:frigo"
    call.from_user.id = 891406979
    call.id = "cb-stale-2"

    await handlers["_callback_query"](call)
    mock_increment.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "changé" in toast.lower()


def test_all_subtask_commands_are_registered():
    """Every entry in menage.SUBTASK_COMMANDS gets a message handler."""
    from src import menage
    bot = Drahmbot()
    handlers = _capture_handlers(bot)
    for cmd in menage.SUBTASK_COMMANDS:
        assert cmd in handlers, f"/{cmd} has no registered handler"

# --- /cendrier: standalone, non-rotating task ---


def test_build_cendrier_keyboard_unchecked():
    kb = _build_cendrier_keyboard(15, False)
    assert len(kb.keyboard) == 1
    assert "⬜" in kb.keyboard[0][0].text
    assert kb.keyboard[0][0].callback_data == "cendrier:15"


def test_build_cendrier_keyboard_checked():
    kb = _build_cendrier_keyboard(15, True)
    assert "✅" in kb.keyboard[0][0].text


def test_build_cendrier_text_not_done():
    text = _build_cendrier_text({})
    assert "Maël" in text
    assert "clique pour marquer" in text


def test_build_cendrier_text_done_by_mael():
    text = _build_cendrier_text({"by": "Maël", "at": "..."})
    assert "vidé par Maël" in text
    assert "✅" in text


def test_build_cendrier_text_done_by_someone_else():
    """Anyone can empty it for him and get credit."""
    text = _build_cendrier_text({"by": "Timon", "at": "..."})
    assert "vidé par Timon" in text
    assert "Maël" in text
    assert "✅" in text


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.get_week_state", return_value={})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_command_sends_keyboard(
    mock_group, mock_token, mock_dt, mock_state,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["cendrier"](message)
    call_args = bot.bot.send_message.call_args
    assert call_args[0][0] == 999
    assert "Maël" in call_args[0][1]
    assert call_args[1]["reply_markup"].keyboard[0][0].callback_data == "cendrier:15"


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state",
       return_value={"by": "Léa", "at": "..."})
@patch("src.drahmbot.cendrier.get_week_state", return_value={})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_callback_anyone_can_mark(
    mock_group, mock_token, mock_dt, mock_state, mock_toggle,
):
    """Léa can mark /cendrier done even though it's Maël's task."""
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
        call.data = "cendrier:15"
        call.from_user.id = 42
        call.id = "cbc1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("Léa")
        bot.bot.edit_message_text.assert_called_once()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "vidé" in toast.lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state")
@patch("src.drahmbot.cendrier.get_week_state", return_value={"by": "Maël", "at": "..."})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_callback_non_doer_cannot_undo(
    mock_group, mock_token, mock_dt, mock_state, mock_toggle,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"  # not Maël, who did it

    try:
        bot = Drahmbot()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "cendrier:15"
        call.from_user.id = 42
        call.id = "cbc2"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "Maël" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_callback_stale_week(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "cendrier:15"
    call.from_user.id = 891406979
    call.id = "cbc3"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "semaine" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_callback_unknown_user(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "cendrier:15"
    call.from_user.id = 99999  # not in TELEGRAM_USER_MAP
    call.id = "cbc4"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "reconnu" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_callback_malformed_data(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "cendrier:15:extra"  # too many parts
    call.from_user.id = 891406979
    call.id = "cbc5"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_cendrier_callback_non_numeric_week(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "cendrier:abc"  # week number isn't an int
    call.from_user.id = 891406979
    call.id = "cbc6"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    toast = bot.bot.answer_callback_query.call_args[0][1]
    assert "invalides" in toast.lower()


# --- /done-embedded cendrier callback ---


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state",
       return_value={"by": "Timon", "at": "..."})
@patch("src.drahmbot.cendrier.get_week_state", return_value={})
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "plan de travail", "rangement"])
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Maël"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_cendrier_callback_rerenders_original_owners_card(
    mock_group, mock_token, mock_dt, mock_assignments, mock_subtasks, mock_status,
    mock_state, mock_toggle,
):
    """Clicking the cendrier row inside someone else's /done message still
    toggles cendrier (anyone can help) but must redraw the ORIGINAL card
    owner's combined view (Maël's), not the clicker's own (Timon's) - the
    row's callback_data embeds the card's role precisely to prevent this."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"  # the clicker, not the card owner

    try:
        bot = Drahmbot()
        bot.bot.edit_message_text = AsyncMock()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "donecendrier:15:CUISINE"
        call.from_user.id = 42
        call.id = "cbc7"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("Timon")
        bot.bot.edit_message_text.assert_called_once()
        edited_text = bot.bot.edit_message_text.call_args[0][0]
        assert "Maël — CUISINE" in edited_text
        assert "Timon — CUISINE" not in edited_text
        # Timon is still rightfully credited as the one who emptied it.
        assert "vidé par Timon" in edited_text
        keyboard = bot.bot.edit_message_text.call_args[1]["reply_markup"]
        assert any(
            btn.callback_data == "donecendrier:15:CUISINE"
            for row in keyboard.keyboard for btn in row
        )
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "vidé" in toast.lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.cendrier.toggle_week_state")
@patch("src.drahmbot.cendrier.get_week_state", return_value={"by": "Maël", "at": "..."})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Maël"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_cendrier_callback_non_doer_cannot_undo(
    mock_group, mock_token, mock_dt, mock_assignments, mock_state, mock_toggle,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    import src.drahmbot as drahmbot_module
    original_map = drahmbot_module.TELEGRAM_USER_MAP.copy()
    drahmbot_module.TELEGRAM_USER_MAP[42] = "Timon"  # not Maël, who did it

    try:
        bot = Drahmbot()
        bot.bot.answer_callback_query = AsyncMock()
        handlers = _capture_handlers(bot)

        call = MagicMock()
        call.data = "donecendrier:15:CUISINE"
        call.from_user.id = 42
        call.id = "cbc8"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "Maël" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


# --- /lavevaisselle: optional counter subtask attached to CUISINE ---


@patch("src.drahmbot.chores.get_week_status", return_value={})
def test_build_done_keyboard_labels_the_optional_row(mock_status):
    """Real CUISINE list (not patched): lave-vaisselle rides along, labelled."""
    keyboard = _build_done_keyboard("CUISINE", 15, "Timon")
    last = keyboard.keyboard[-1][0]
    assert last.callback_data == "done:15:CUISINE:lave-vaisselle"
    assert "(0x, optionnel)" in last.text


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "frigo": {"by": "Timon", "at": "..."},
        "plan de travail": {"count": 1, "by": "Timon", "at": "..."},
        "rangement": {"by": "Timon", "at": "..."},
        "balcon": {"by": "Timon", "at": "..."},
    }},
})
def test_build_done_text_score_ignores_the_optional_subtask(mock_status):
    """4/4 and a ✅ even with lave-vaisselle untouched: it never drags the score."""
    text = _build_done_text("CUISINE", "Timon")
    assert "4/4" in text
    assert "✅" in text
    assert "(optionnel) lave-vaisselle : 0x" in text


@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "lave-vaisselle": {"count": 3, "by": "Léa", "at": "...", "doers": {"Léa"}},
    }},
})
def test_build_done_text_shows_the_optional_count(mock_status):
    text = _build_done_text("CUISINE", "Timon")
    assert "0/4" in text
    assert "(optionnel) lave-vaisselle : 3x" in text


def test_build_counter_text_optional_names_no_assignee():
    text = _build_counter_text("CUISINE", "lave-vaisselle", "Timon", 0)
    assert "optionnel" in text
    assert "Timon" not in text


def test_build_counter_text_optional_positive():
    text = _build_counter_text("CUISINE", "lave-vaisselle", "Timon", 5)
    assert "5x" in text
    assert "optionnel" in text
    assert "✅" in text


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {
        "lave-vaisselle": {"count": 2, "by": "Léa", "at": "...", "doers": {"Léa"}},
    }},
})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_lavevaisselle_command_sends_counter_keyboard(
    mock_group, mock_token, mock_dt, mock_assignments, mock_status,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["lavevaisselle"](message)
    call_args = bot.bot.send_message.call_args
    text = call_args[0][1]
    assert "2x" in text
    assert "optionnel" in text
    keyboard = call_args[1]["reply_markup"]
    assert keyboard.keyboard[0][0].callback_data == "counter:15:lavevaisselle"


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "lave-vaisselle"])
@patch("src.drahmbot.chores.increment_subtask_counter",
       return_value={"count": 1, "counts": {"Léa": 1}})
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.menage.get_role_for_person", return_value="SOLs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_callback_optional_row_accepts_anyone_and_rerenders_for_the_owner(
    mock_group, mock_token, mock_dt, mock_role, mock_assignments, mock_increment,
    mock_subtasks, mock_status,
):
    """Léa has SOLs, yet she can tick lave-vaisselle from Timon's /done card;
    the card must still come back rendered for Timon."""
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
        call.data = "done:15:CUISINE:lave-vaisselle"
        call.from_user.id = 42
        call.id = "cb-lv-1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_increment.assert_called_once_with("CUISINE", "lave-vaisselle", "Léa")
        text = bot.bot.edit_message_text.call_args[0][0]
        assert "Timon" in text
        assert "Léa" not in text
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "1x" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo", "lave-vaisselle"])
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.menage.get_role_for_person", return_value="SOLs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_callback_still_rejects_a_required_subtask_of_someone_elses_role(
    mock_group, mock_token, mock_dt, mock_role, mock_toggle, mock_subtasks, mock_status,
):
    """The optional exemption is per-subtask: frigo is still Timon's alone."""
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
        call.data = "done:15:CUISINE:frigo"
        call.from_user.id = 42
        call.id = "cb-lv-2"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "pas ta tâche" in toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


def test_build_commands_text_annotates_optional_and_counter_subtasks():
    lines = _build_commands_text().split("\n")
    assert "/lavevaisselle (optionnel, compteur)" in lines
    assert "/plandetravail (compteur)" in lines
    assert "/frigo" in lines


# --- optional toggle subtask: open to tick, doer-only to untick ---


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={
    "CUISINE": {"subtasks": {"frigo": {"by": "Timon", "at": "..."}}},
})
@patch("src.drahmbot.menage.is_optional_subtask", return_value=True)
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo"])
@patch("src.drahmbot.chores.toggle_subtask")
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.menage.get_role_for_person", return_value="SOLs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_callback_optional_toggle_cannot_be_undone_by_a_non_doer(
    mock_group, mock_token, mock_dt, mock_role, mock_assignments, mock_toggle,
    mock_subtasks, mock_optional, mock_status,
):
    """The optional bypass lets anyone tick, but must not let them un-tick
    someone else's work (same rule as the /frigo-style buttons). Uses a
    patched optional *toggle* subtask: OPTIONAL_SUBTASKS and COUNTER_SUBTASKS
    are independent registries, so this combination is one config line away."""
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
        call.data = "done:15:CUISINE:frigo"
        call.from_user.id = 42
        call.id = "cb-opt-toggle-1"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        bot.bot.edit_message_text.assert_not_called()
        toast = bot.bot.answer_callback_query.call_args[0][1]
        assert "Seul·e Timon peut annuler." == toast
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chores.get_week_status", return_value={})
@patch("src.drahmbot.menage.is_optional_subtask", return_value=True)
@patch("src.drahmbot.menage.get_subtasks_for_role", return_value=["frigo"])
@patch("src.drahmbot.chores.toggle_subtask", return_value=True)
@patch("src.drahmbot.menage.get_role_assignments", return_value={"CUISINE": "Timon"})
@patch("src.drahmbot.menage.get_role_for_person", return_value="SOLs")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_done_callback_optional_toggle_can_be_ticked_by_anyone(
    mock_group, mock_token, mock_dt, mock_role, mock_assignments, mock_toggle,
    mock_subtasks, mock_optional, mock_status,
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
        call.data = "done:15:CUISINE:frigo"
        call.from_user.id = 42
        call.id = "cb-opt-toggle-2"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("CUISINE", "frigo", "Léa")
        text = bot.bot.edit_message_text.call_args[0][0]
        assert "Timon" in text  # still the card owner's view
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


# --- /chiffons: unassigned, optional, done/undone ---


def test_build_chiffons_keyboard_unchecked():
    kb = _build_chiffons_keyboard(15, False)
    assert len(kb.keyboard) == 1
    assert "⬜" in kb.keyboard[0][0].text
    assert kb.keyboard[0][0].callback_data == "chiffons:15"


def test_build_chiffons_keyboard_checked():
    kb = _build_chiffons_keyboard(15, True)
    assert "✅" in kb.keyboard[0][0].text


def test_build_chiffons_text_done_this_week():
    text = _build_chiffons_text({"by": "Léa", "at": "..."})
    assert "Léa" in text
    assert "✅" in text
    assert "corvée" not in text  # nothing to nag about, it's done


def test_build_chiffons_text_not_done_names_nobody_as_responsible():
    text = _build_chiffons_text({}, last_done=None)
    assert "Personne n'est de corvée" in text
    assert "au moins 8 semaines" in text


def test_build_chiffons_text_reports_the_previous_wash():
    text = _build_chiffons_text({}, last_done=(3, {"by": "Timon", "at": "..."}))
    assert "il y a 3 semaines, par Timon" in text


def test_build_chiffons_text_last_week_reads_naturally():
    text = _build_chiffons_text({}, last_done=(1, {"by": "Timon", "at": "..."}))
    assert "la semaine dernière, par Timon" in text


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.get_last_done", return_value=(2, {"by": "Timon", "at": "..."}))
@patch("src.drahmbot.chiffons.get_week_state", return_value={})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_command_sends_keyboard(
    mock_group, mock_token, mock_dt, mock_state, mock_last,
):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["chiffons"](message)
    call_args = bot.bot.send_message.call_args
    assert "il y a 2 semaines, par Timon" in call_args[0][1]
    assert call_args[1]["reply_markup"].keyboard[0][0].callback_data == "chiffons:15"


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.get_last_done")
@patch("src.drahmbot.chiffons.get_week_state", return_value={"by": "Léa", "at": "..."})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_command_skips_the_lookback_when_already_done(
    mock_group, mock_token, mock_dt, mock_state, mock_last,
):
    """get_last_done costs one get_item per week looked back, so don't pay
    for it when this week already answers the question."""
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)
    bot = Drahmbot()
    bot.bot.send_message = AsyncMock()
    handlers = _capture_handlers(bot)

    message = MagicMock()
    message.chat.id = 999

    await handlers["chiffons"](message)
    mock_last.assert_not_called()


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.get_last_done", return_value=None)
@patch("src.drahmbot.chiffons.toggle_week_state", return_value={"by": "Léa", "at": "..."})
@patch("src.drahmbot.chiffons.get_week_state", return_value={})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_callback_anyone_can_mark(
    mock_group, mock_token, mock_dt, mock_state, mock_toggle, mock_last,
):
    """Nobody is assigned, so any colocataire can claim it."""
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
        call.data = "chiffons:15"
        call.from_user.id = 42
        call.id = "cbch1"
        call.message.chat.id = 999
        call.message.message_id = 100

        await handlers["_callback_query"](call)
        mock_toggle.assert_called_once_with("Léa")
        assert "Léa" in bot.bot.edit_message_text.call_args[0][0]
        assert "chiffons" in bot.bot.answer_callback_query.call_args[0][1].lower()
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.toggle_week_state")
@patch("src.drahmbot.chiffons.get_week_state", return_value={"by": "Timon", "at": "..."})
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_callback_non_doer_cannot_undo(
    mock_group, mock_token, mock_dt, mock_state, mock_toggle,
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
        call.data = "chiffons:15"
        call.from_user.id = 42
        call.id = "cbch2"

        await handlers["_callback_query"](call)
        mock_toggle.assert_not_called()
        assert "Seul·e Timon peut annuler." == bot.bot.answer_callback_query.call_args[0][1]
    finally:
        drahmbot_module.TELEGRAM_USER_MAP.clear()
        drahmbot_module.TELEGRAM_USER_MAP.update(original_map)


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_callback_stale_week(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 16, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "chiffons:15"
    call.from_user.id = 891406979
    call.id = "cbch3"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    assert "semaine" in bot.bot.answer_callback_query.call_args[0][1].lower()


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_callback_unknown_user(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    call = MagicMock()
    call.data = "chiffons:15"
    call.from_user.id = 99999  # not in TELEGRAM_USER_MAP
    call.id = "cbch4"

    await handlers["_callback_query"](call)
    mock_toggle.assert_not_called()
    assert "reconnu" in bot.bot.answer_callback_query.call_args[0][1]


@pytest.mark.asyncio
@patch("src.drahmbot.chiffons.toggle_week_state")
@patch("src.drahmbot.datetime")
@patch("src.drahmbot.utils.get_token", return_value="12345:12345")
@patch("src.drahmbot.utils.get_group_id", return_value=123)
async def test_chiffons_callback_malformed_data(mock_group, mock_token, mock_dt, mock_toggle):
    mock_dt.date.today.return_value.isocalendar.return_value = (2026, 15, 1)

    bot = Drahmbot()
    bot.bot.answer_callback_query = AsyncMock()
    handlers = _capture_handlers(bot)

    for data in ("chiffons:", "chiffons:pasunnombre", "chiffons:15:extra"):
        call = MagicMock()
        call.data = data
        call.from_user.id = 891406979
        call.id = "cbch5"
        await handlers["_callback_query"](call)
        assert "invalides" in bot.bot.answer_callback_query.call_args[0][1]
    mock_toggle.assert_not_called()
