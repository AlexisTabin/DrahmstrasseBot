import json
import logging
import telebot

from telebot.async_telebot import AsyncTeleBot
import src.utils as utils
import src.menage as menage
import src.social as social
import src.chores as chores

# Setup logging
logger = logging.getLogger(__name__)

# Constants
LEA = 'Léa'
TIMON = 'Timon'
MAEL = 'Maël'
ALEXIS = 'Alexis'
colocataires = [TIMON, MAEL, LEA, ALEXIS]

# Map Telegram user IDs to colocataire names.
# Populate by having each person send /myid in the group chat.
TELEGRAM_USER_MAP = {}

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
            return
        self.token = token or utils.get_token()
        self.chat_id = chat_id or utils.get_group_id()
        self.bot = AsyncTeleBot(self.token, parse_mode=None)
        logger.info("Initializing Drahmbot with chat_id: %s", self.chat_id)
        self.register_handlers()
        self._initialized = True
        logger.info("Drahmbot initialization complete")

    def register_handlers(self):
        logger.info("Registering command handlers")

        @self.bot.message_handler(commands=['roles'])
        async def send_roles(message):
            logger.info("Command /roles received from %s", message.chat.id)
            answer = menage.getRoles(colocataires=colocataires)
            await self.bot.send_message(message.chat.id, answer)
            logger.info("Sent roles answer: %s", answer)

        @self.bot.message_handler(commands=['papier'])
        async def send_papier(message):
            logger.info("Command /papier received from %s", message.chat.id)
            answer = menage.get_papier_reminder(colocataires=colocataires)
            await self.bot.send_message(message.chat.id, answer)
            logger.info("Sent papier answer: %s", answer)

        @self.bot.message_handler(commands=['carton'])
        async def send_carton(message):
            logger.info("Command /carton received from %s", message.chat.id)
            answer = menage.get_carton_reminder(colocataires=colocataires)
            await self.bot.send_message(message.chat.id, answer)
            logger.info("Sent carton answer: %s", answer)

        @self.bot.message_handler(commands=['lessive'])
        async def send_lessive(message):
            logger.info("Command /lessive received from %s", message.chat.id)
            answer = menage.getCarteDeLessive()
            await self.bot.send_message(message.chat.id, answer)
            logger.info("Sent lessive answer: %s", answer)

        @self.bot.message_handler(commands=['whoishere'])
        async def whosthere(message):
            logger.info("Command /whoishere received from %s", message.chat.id)
            question = social.is_present_dinner()
            await self.bot.send_poll(
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

        @self.bot.message_handler(commands=['myid'])
        async def send_myid(message):
            user = message.from_user
            user_id = user.id if user else None
            logger.info("Command /myid received from user_id=%s", user_id)
            if user_id:
                first = user.first_name or ""
                last = user.last_name or ""
                name = f"{first} {last}".strip()
                answer = f"Ton ID Telegram : {user_id} ({name})"
            else:
                answer = "Impossible de récupérer ton ID."
            await self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(commands=['done'])
        async def mark_done(message):
            user_id = message.from_user.id if message.from_user else None
            logger.info("Command /done received from user_id=%s", user_id)

            person = TELEGRAM_USER_MAP.get(user_id)
            if not person:
                await self.bot.send_message(
                    message.chat.id,
                    "Je ne sais pas qui tu es ! Envoie /myid d'abord, "
                    "puis demande à un admin d'ajouter ton ID.",
                )
                return

            role = menage.get_role_for_person(colocataires, person)
            if not role:
                await self.bot.send_message(
                    message.chat.id,
                    f"{person}, tu n'as pas de rôle attribué cette semaine.",
                )
                return

            newly_done = chores.mark_done(role, person)
            if newly_done:
                answer = f"Bien joué {person} ! {role} marqué comme fait."
            else:
                answer = f"{role} est déjà marqué comme fait cette semaine."
            await self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(commands=['reminder'])
        async def send_reminder(message):
            logger.info("Command /reminder received from %s", message.chat.id)
            assignments = menage.get_role_assignments(colocataires)
            answer = chores.get_thursday_reminder(assignments)
            await self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(commands=['recap'])
        async def send_recap(message):
            logger.info("Command /recap received from %s", message.chat.id)
            assignments = menage.get_role_assignments(colocataires)
            answer = chores.get_sunday_recap(assignments)
            await self.bot.send_message(message.chat.id, answer)

        @self.bot.message_handler(regexp='jeremie?')
        async def jeremied(message):
            logger.info("Regexp 'jeremie?' matched by %s", message.chat.id)
            await self.bot.reply_to(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")
            logger.info("Replied with Jeremie's message")

    async def process_update(self, update_json):
        """Process a single update (for testing or Lambda)."""
        logger.info("Processing update: %s", update_json)
        update = telebot.types.Update.de_json(update_json)
        await self.bot.process_new_updates([update])
        logger.info("Update processed successfully")
