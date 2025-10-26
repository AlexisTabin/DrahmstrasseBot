
import json
import telebot
import src.utils as utils
import src.menage as menage
import src.social as social


# Constants
LEA = 'Lea'
MARGAUX = 'Margaux'
TIMON = 'timon'
MAEL = 'Maël'
ALEXIS = 'Alexis'

colocataires = [MARGAUX, MAEL, LEA, ALEXIS]

class Drahmbot:
    _instance = None  # Singleton instance

    def __new__(cls, token=None, chat_id=None):
        if cls._instance is None:
            cls._instance = super(Drahmbot, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, token=None, chat_id=None):
        if self._initialized:
            return  # Avoid re-initializing singleton

        self.token = token or utils.get_token()
        self.chat_id = chat_id or utils.get_group_id()
        self.bot = telebot.TeleBot(self.token, parse_mode=None)

        # Register handlers
        self.register_handlers()

        self._initialized = True

    def register_handlers(self):
        @self.bot.message_handler(commands=['roles'])
        def send_roles(message):
            answer = menage.getRoles(colocataires=colocataires)
            self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(commands=['papier'])
        def send_papier_ou_carton(message):
            answer = menage.getCartonOrPapier()
            self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(commands=['lessive'])
        def send_lessive(message):
            answer = menage.getCarteDeLessive()
            self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(commands=['whoishere'])
        def whosthere(message):
            question = social.is_present_dinner()
            self.bot.send_poll(
                message.chat.id,
                question,
                [
                    'Oui',
                    'Oui INTO je ramène un.e +1',
                    'Oui INTO je cuisine',
                    'Oui, je cuisine ET je ramène un.e +1',
                    "C'est ciao",
                ],
                is_anonymous=False,
            )

        @self.bot.message_handler(regexp='jeremie?')
        def jeremied(message):
            self.bot.reply_to(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")

    def process_update(self, update_json):
        """Process a single update (for testing or Lambda)."""
        update = telebot.types.Update.de_json(update_json)
        self.bot.process_new_updates([update])

    def start_polling(self):
        """Starts the bot in polling mode (for local testing)."""
        self.bot.infinity_polling()
