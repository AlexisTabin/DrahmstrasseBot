import json
import telebot
import logging
import src.utils as utils
import src.menage as menage
import src.social as social

# Setup logging
logger = logging.getLogger(__name__)

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
            logger.info("Creating new Drahmbot instance")
        return cls._instance

    def __init__(self, token=None, chat_id=None):
        if self._initialized:
            logger.info("Drahmbot already initialized, skipping __init__")
            return  # Avoid re-initializing singleton

        self.token = token or utils.get_token()
        self.chat_id = chat_id or utils.get_group_id()
        self.bot = telebot.TeleBot(self.token, parse_mode=None)

        logger.info("Initializing Drahmbot with chat_id: %s", self.chat_id)

        # Register handlers
        self.register_handlers()

        self._initialized = True
        logger.info("Drahmbot initialization complete")

    def register_handlers(self):
        logger.info("Registering command handlers")

        @self.bot.message_handler(commands=['roles'])
        def send_roles(message):
            logger.info("Command /roles received from %s", message.chat.id)
            answer = menage.getRoles(colocataires=colocataires)
            self.bot.send_message(message.chat.id, answer)
            logger.info("Sent roles answer: %s", answer)

        @self.bot.message_handler(commands=['papier'])
        def send_papier_ou_carton(message):
            logger.info("Command /papier received from %s", message.chat.id)
            answer = menage.getCartonOrPapier()
            self.bot.send_message(message.chat.id, answer)
            logger.info("Sent papier/carton answer: %s", answer)

        @self.bot.message_handler(commands=['lessive'])
        def send_lessive(message):
            logger.info("Command /lessive received from %s", message.chat.id)
            answer = menage.getCarteDeLessive()
            self.bot.send_message(message.chat.id, answer)
            logger.info("Sent lessive answer: %s", answer)

        @self.bot.message_handler(commands=['whoishere'])
        def whosthere(message):
            logger.info("Command /whoishere received from %s", message.chat.id)
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
            logger.info("Sent whoishere poll with question: %s", question)

        @self.bot.message_handler(regexp='jeremie?')
        def jeremied(message):
            logger.info("Regexp 'jeremie?' matched by %s", message.chat.id)
            self.bot.reply_to(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")
            logger.info("Replied with Jeremie's message")

    def process_update(self, update_json):
        """Process a single update (for testing or Lambda)."""
        logger.info("Processing update: %s", update_json)
        update = telebot.types.Update.de_json(update_json)
        self.bot.process_new_updates([update])
        logger.info("Update processed successfully")

    def start_polling(self):
        """Starts the bot in polling mode (for local testing)."""
        logger.info("Starting polling...")
        self.bot.infinity_polling()
        logger.info("Polling stopped")

