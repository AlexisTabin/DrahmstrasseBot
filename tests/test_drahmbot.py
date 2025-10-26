import pytest
from unittest.mock import patch, MagicMock
import src.drahmbot as drahmbot

@pytest.fixture(autouse=True)
def reset_singleton():
    # Reset the singleton before each test
    drahmbot.Drahmbot._instance = None
    yield
    drahmbot.Drahmbot._instance = None

def test_singleton_behavior():
    with patch("src.drahmbot.utils.get_token", return_value="token"), \
         patch("src.drahmbot.utils.get_group_id", return_value="chat_id"), \
         patch("src.drahmbot.telebot.TeleBot") as MockTeleBot:

        bot1 = drahmbot.Drahmbot()
        bot2 = drahmbot.Drahmbot()
        
        # Same instance should be returned
        assert bot1 is bot2
        # __init__ should not reinitialize
        assert bot1.token == "token"
        assert bot1.chat_id == "chat_id"
        MockTeleBot.assert_called_once_with("token", parse_mode=None)


def test_handlers_call_correct_functions():
    with patch("src.drahmbot.menage.getRoles", return_value="roles_answer") as mock_roles, \
         patch("src.drahmbot.menage.getCartonOrPapier", return_value="papier_answer") as mock_papier, \
         patch("src.drahmbot.menage.getCarteDeLessive", return_value="lessive_answer") as mock_lessive, \
         patch("src.drahmbot.social.is_present_dinner", return_value="dinner_question") as mock_social, \
         patch("src.drahmbot.utils.get_token", return_value="token"), \
         patch("src.drahmbot.utils.get_group_id", return_value="chat_id"), \
         patch("src.drahmbot.telebot.TeleBot") as MockTeleBot:

        mock_bot_instance = MockTeleBot.return_value

        # Handlers just register functions via decorators; we can capture them
        registered_handlers = {}
        def fake_message_handler(*args, **kwargs):
            def decorator(func):
                registered_handlers[tuple(kwargs.get("commands", [])) or kwargs.get("regexp")] = func
                return func
            return decorator
        mock_bot_instance.message_handler.side_effect = fake_message_handler

        bot = drahmbot.Drahmbot()

        # Test /roles handler
        message = MagicMock()
        message.chat.id = "chat_id"
        registered_handlers[('roles',)](message)
        mock_roles.assert_called_once()
        mock_bot_instance.send_message.assert_called_with("chat_id", "roles_answer")

        # Test /papier handler
        registered_handlers[('papier',)](message)
        mock_papier.assert_called_once()
        mock_bot_instance.send_message.assert_called_with("chat_id", "papier_answer")

        # Test /lessive handler
        registered_handlers[('lessive',)](message)
        mock_lessive.assert_called_once()
        mock_bot_instance.send_message.assert_called_with("chat_id", "lessive_answer")

        # Test /whoishere handler
        registered_handlers[('whoishere',)](message)
        mock_social.assert_called_once()
        mock_bot_instance.send_poll.assert_called_with(
            "chat_id",
            "dinner_question",
            [
                'Oui',
                'Oui INTO je ramène un.e +1',
                'Oui INTO je cuisine',
                'Oui, je cuisine ET je ramène un.e +1',
                "C'est ciao",
            ],
            is_anonymous=False,
        )

        # Test regexp "jeremie" handler
        jeremie_message = MagicMock()
        jeremie_message.text = "jeremie"
        registered_handlers['jeremie?'](jeremie_message)
        mock_bot_instance.reply_to.assert_called_with(jeremie_message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")


def test_process_update_calls_process_new_updates():
    with patch("src.drahmbot.utils.get_token", return_value="token"), \
         patch("src.drahmbot.utils.get_group_id", return_value="chat_id"), \
         patch("src.drahmbot.telebot.TeleBot") as MockTeleBot, \
         patch("src.drahmbot.telebot.types.Update.de_json") as mock_de_json:

        mock_bot_instance = MockTeleBot.return_value
        mock_update = MagicMock()
        mock_de_json.return_value = mock_update
        bot = drahmbot.Drahmbot()

        bot.process_update('{"update_id":123}')
        mock_de_json.assert_called_once_with('{"update_id":123}')
        mock_bot_instance.process_new_updates.assert_called_once_with([mock_update])


def test_start_polling_calls_infinity_polling():
    with patch("src.drahmbot.utils.get_token", return_value="token"), \
         patch("src.drahmbot.utils.get_group_id", return_value="chat_id"), \
         patch("src.drahmbot.telebot.TeleBot") as MockTeleBot:

        mock_bot_instance = MockTeleBot.return_value
        bot = drahmbot.Drahmbot()
        bot.start_polling()
        mock_bot_instance.infinity_polling.assert_called_once()

