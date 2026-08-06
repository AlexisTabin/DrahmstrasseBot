import datetime
import json
import logging
import random
import telebot

from telebot.async_telebot import AsyncTeleBot
from telebot.handler_backends import BaseMiddleware, CancelUpdate
import src.utils as utils
import src.menage as menage
import src.social as social
import src.chores as chores
import src.phrases as phrases
import src.plants as plants
import src.weather as weather
import src.cendrier as cendrier

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
TELEGRAM_USER_MAP = {
    5503636012: LEA,
    891406979: ALEXIS,
    981443207: MAEL,
    1645783874: TIMON,
}

class ColocAccessMiddleware(BaseMiddleware):
    def __init__(self, user_map):
        super().__init__()
        self.user_map = user_map
        self.update_types = ['message', 'callback_query']

    async def pre_process(self, message, data):
        from_user = message.from_user
        if from_user is None:
            return
        if hasattr(message, 'text') and message.text and message.text.strip().startswith('/myid'):
            return
        if from_user.id not in self.user_map:
            return CancelUpdate()

    async def post_process(self, message, data, exception):
        pass


def _build_done_keyboard(role, week_num):
    """Build an InlineKeyboardMarkup for a role's done status."""
    subtasks = menage.get_subtasks_for_role(role)
    keyboard = telebot.types.InlineKeyboardMarkup()

    completed = chores.get_week_status()
    role_data = completed.get(role, {})

    if subtasks is None:
        is_done = "by" in role_data
        icon = "\u2705" if is_done else "\u2b1c"
        button = telebot.types.InlineKeyboardButton(
            text=f"{icon} {role}",
            callback_data=f"done:{week_num}:{role}",
        )
        keyboard.add(button)
    else:
        completed_subtasks = role_data.get("subtasks", {})
        for subtask in subtasks:
            is_done = subtask in completed_subtasks
            icon = "\u2705" if is_done else "\u2b1c"
            button = telebot.types.InlineKeyboardButton(
                text=f"{icon} {subtask}",
                callback_data=f"done:{week_num}:{role}:{subtask}",
            )
            keyboard.add(button)

    return keyboard


def _build_done_text(role, person):
    """Build status text for a role's done message."""
    subtasks = menage.get_subtasks_for_role(role)
    completed = chores.get_week_status()
    role_data = completed.get(role, {})

    if subtasks is None:
        is_done = "by" in role_data
        if is_done:
            return f"{person} \u2014 {role} : fait \u2705"
        return f"{person} \u2014 {role} : clique pour marquer comme fait."
    else:
        completed_subtasks = role_data.get("subtasks", {})
        done_count = sum(1 for s in subtasks if s in completed_subtasks)
        total = len(subtasks)
        if done_count == total:
            return f"{person} \u2014 {role} : {done_count}/{total} sous-t\u00e2ches faites \u2705"
        return f"{person} \u2014 {role} : {done_count}/{total} sous-t\u00e2ches faites."


def _build_plants_keyboard(date_iso, watered):
    """Single toggleable button: 'J'ai arrosé !' Re-clicking unmarks."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    icon = "✅" if watered else "⬜"
    keyboard.add(telebot.types.InlineKeyboardButton(
        text=f"{icon} {phrases.ARROSAGE_LABEL_WATERED}",
        callback_data=f"plants:{date_iso}",
    ))
    return keyboard


def _pick_arrosage_header(date_iso):
    """Pick a header phrase deterministically per date so edits stay stable."""
    rng = random.Random(f"drahmbot-arrosage-{date_iso}")
    return rng.choice(phrases.ARROSAGE_HEADER)


def _build_plants_text(date_iso, temp_c, state_data):
    """Build status text for the watering message."""
    header = _pick_arrosage_header(date_iso).format(temp=round(temp_c))
    if not plants.is_watered(state_data):
        return header
    by = state_data.get("by", "?")
    return f"{header}\n\n\U0001f4a7 {by} a arrosé les plantes."


def _build_dechets_keyboard(week_num, subtask, role_data):
    """Single toggleable button for a DÉCHETS subtask (papier/carton)."""
    subtasks = role_data.get("subtasks", {})
    is_done = subtask in subtasks
    icon = "✅" if is_done else "⬜"
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(
        text=f"{icon} J'ai sorti le {subtask} !",
        callback_data=f"dechets:{week_num}:{subtask}",
    ))
    return keyboard


def _build_dechets_text(base_text, subtask, role_data):
    """Append a doer line to the reminder text once someone marks it done."""
    sub_data = role_data.get("subtasks", {}).get(subtask)
    if not sub_data:
        return base_text
    by = sub_data.get("by", "?")
    return f"{base_text}\n\n✅ {by} a sorti le {subtask}."


def _build_subtask_keyboard(week_num, cmd, is_done):
    """Single toggleable button for a generic per-subtask command (e.g. /frigo)."""
    icon = "✅" if is_done else "⬜"
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(
        text=f"{icon} marquer comme fait",
        callback_data=f"subtask:{week_num}:{cmd}",
    ))
    return keyboard


def _build_subtask_text(role, subtask, assigned_person, sub_data):
    """Status text for a generic per-subtask command, crediting whoever did it."""
    if not sub_data:
        return f"{subtask} ({role}, tâche de {assigned_person}) : clique pour marquer comme fait."
    by = sub_data.get("by", "?")
    if by == assigned_person:
        return f"{subtask} ({role}) : fait par {by} ✅"
    return f"{subtask} ({role}, tâche de {assigned_person}) : fait par {by} \U0001f91d ✅"


def _build_cendrier_keyboard(week_num, is_done):
    """Single toggleable button for the standalone /cendrier command."""
    icon = "✅" if is_done else "⬜"
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(
        text=f"{icon} J'ai vidé le cendrier !",
        callback_data=f"cendrier:{week_num}",
    ))
    return keyboard


def _build_cendrier_text(state):
    """Status text for the standalone /cendrier command, crediting whoever did it."""
    if not state:
        return f"Cendrier ({MAEL}) : clique pour marquer comme vidé cette semaine."
    by = state.get("by", "?")
    if by == MAEL:
        return f"Cendrier vidé par {by} cette semaine ✅"
    return f"Cendrier ({MAEL}) : vidé par {by} \U0001f91d ✅"


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
        self.dev_chat_id = utils.get_dev_chat_id()
        self.bot = AsyncTeleBot(self.token, parse_mode=None)
        self.bot.use_class_middlewares = True
        logger.info("Initializing Drahmbot with chat_id: %s", self.chat_id)
        self.bot.setup_middleware(ColocAccessMiddleware(TELEGRAM_USER_MAP))
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
            if not utils.is_even_week():
                logger.info("Odd week — skipping papier reminder")
                return
            base = menage.get_papier_reminder(colocataires=colocataires)
            week_num = datetime.date.today().isocalendar()[1]
            role_data = chores.get_week_status().get("DÉCHETS", {})
            text = _build_dechets_text(base, "papier", role_data)
            keyboard = _build_dechets_keyboard(week_num, "papier", role_data)
            await self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
            logger.info("Sent papier answer: %s", text)

        @self.bot.message_handler(commands=['carton'])
        async def send_carton(message):
            logger.info("Command /carton received from %s", message.chat.id)
            base = menage.get_carton_reminder(colocataires=colocataires)
            week_num = datetime.date.today().isocalendar()[1]
            role_data = chores.get_week_status().get("DÉCHETS", {})
            text = _build_dechets_text(base, "carton", role_data)
            keyboard = _build_dechets_keyboard(week_num, "carton", role_data)
            await self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
            logger.info("Sent carton answer: %s", text)

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

            week_num = datetime.date.today().isocalendar()[1]
            keyboard = _build_done_keyboard(role, week_num)
            text = _build_done_text(role, person)
            await self.bot.send_message(message.chat.id, text, reply_markup=keyboard)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("done:"))
        async def handle_done_callback(call):
            parts = call.data.split(":")
            if len(parts) < 3:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return

            week_num = int(parts[1])
            role = parts[2]
            subtask = parts[3] if len(parts) > 3 else None

            current_week = datetime.date.today().isocalendar()[1]
            if week_num != current_week:
                await self.bot.answer_callback_query(
                    call.id, "Cette semaine est terminée.", show_alert=True,
                )
                return

            user_id = call.from_user.id
            person = TELEGRAM_USER_MAP.get(user_id)
            if not person:
                await self.bot.answer_callback_query(
                    call.id, "Tu n'es pas reconnu.", show_alert=True,
                )
                return

            assigned_role = menage.get_role_for_person(colocataires, person)
            if assigned_role != role:
                await self.bot.answer_callback_query(
                    call.id, "Ce n'est pas ta tâche !", show_alert=True,
                )
                return

            if subtask:
                valid_subtasks = menage.get_subtasks_for_role(role)
                if valid_subtasks is None or subtask not in valid_subtasks:
                    await self.bot.answer_callback_query(
                        call.id, "Sous-tâche inconnue.", show_alert=True,
                    )
                    return
                now_done = chores.toggle_subtask(role, subtask, person)
                toast = f"{subtask} fait !" if now_done else f"{subtask} annulé."
            else:
                now_done = chores.toggle_role(role, person)
                toast = f"{role} fait !" if now_done else f"{role} annulé."

            keyboard = _build_done_keyboard(role, week_num)
            text = _build_done_text(role, person)
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
            await self.bot.answer_callback_query(call.id, toast)

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

        @self.bot.message_handler(commands=['arrosage'])
        async def send_arrosage(message):
            logger.info("Command /arrosage received from %s", message.chat.id)
            max_temp = weather.get_zurich_max_temp_today()
            if max_temp is None:
                logger.info("Skipping arrosage: weather unavailable")
                return

            if max_temp >= weather.HOT_THRESHOLD_C:
                should_remind = True
            elif max_temp >= weather.WARM_THRESHOLD_C:
                last_watered = plants.get_last_watered_date()
                today = datetime.date.today()
                days_since = (
                    (today - last_watered).days
                    if last_watered is not None
                    else weather.WARM_BAND_COOLDOWN_DAYS
                )
                should_remind = days_since >= weather.WARM_BAND_COOLDOWN_DAYS
                logger.info(
                    "Warm band: max=%.1f last_watered=%s days_since=%s remind=%s",
                    max_temp, last_watered, days_since, should_remind,
                )
            else:
                should_remind = False
                logger.info("Cool day, skipping: max_temp=%.1f", max_temp)

            if not should_remind:
                return

            today_iso = datetime.date.today().isoformat()
            state_data = plants.get_today_state()
            keyboard = _build_plants_keyboard(today_iso, plants.is_watered(state_data))
            text = _build_plants_text(today_iso, max_temp, state_data)
            await self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
            logger.info("Sent arrosage message (max_temp=%.1f)", max_temp)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("plants:"))
        async def handle_plants_callback(call):
            parts = call.data.split(":")
            if len(parts) != 2:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return

            date_iso = parts[1]

            today_iso = datetime.date.today().isoformat()
            if date_iso != today_iso:
                await self.bot.answer_callback_query(
                    call.id, "Trop tard, le vote d'arrosage est clos.", show_alert=True,
                )
                return

            user_id = call.from_user.id
            person = TELEGRAM_USER_MAP.get(user_id)
            if not person:
                await self.bot.answer_callback_query(
                    call.id, "Tu n'es pas reconnu.", show_alert=True,
                )
                return

            state_data = plants.toggle_today_state(person)
            now_watered = plants.is_watered(state_data)
            toast = "Merci, c'est noté !" if now_watered else "Annulé."

            max_temp = weather.get_zurich_max_temp_today()
            if max_temp is None:
                max_temp = weather.HOT_THRESHOLD_C  # fallback so format() works

            keyboard = _build_plants_keyboard(date_iso, now_watered)
            text = _build_plants_text(date_iso, max_temp, state_data)
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
            await self.bot.answer_callback_query(call.id, toast)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("dechets:"))
        async def handle_dechets_callback(call):
            parts = call.data.split(":")
            if len(parts) != 3:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return

            try:
                week_num = int(parts[1])
            except ValueError:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return
            subtask = parts[2]

            current_week = datetime.date.today().isocalendar()[1]
            if week_num != current_week:
                await self.bot.answer_callback_query(
                    call.id, "Trop tard, c'est une autre semaine.", show_alert=True,
                )
                return

            user_id = call.from_user.id
            person = TELEGRAM_USER_MAP.get(user_id)
            if not person:
                await self.bot.answer_callback_query(
                    call.id, "Tu n'es pas reconnu.", show_alert=True,
                )
                return

            valid_subtasks = menage.get_subtasks_for_role("DÉCHETS")
            if valid_subtasks is None or subtask not in valid_subtasks:
                await self.bot.answer_callback_query(
                    call.id, "Sous-tâche inconnue.", show_alert=True,
                )
                return

            role_data = chores.get_week_status().get("DÉCHETS", {})
            existing = role_data.get("subtasks", {}).get(subtask)
            # Only the doer may untoggle. Open click to mark; restricted undo.
            if existing and existing.get("by") != person:
                await self.bot.answer_callback_query(
                    call.id,
                    f"Seul·e {existing['by']} peut annuler.",
                    show_alert=True,
                )
                return

            now_done = chores.toggle_subtask("DÉCHETS", subtask, person)
            toast = f"{subtask} fait !" if now_done else f"{subtask} annulé."

            if subtask == "papier":
                base = menage.get_papier_reminder(colocataires=colocataires)
            else:
                base = menage.get_carton_reminder(colocataires=colocataires)
            new_role_data = chores.get_week_status().get("DÉCHETS", {})
            text = _build_dechets_text(base, subtask, new_role_data)
            keyboard = _build_dechets_keyboard(week_num, subtask, new_role_data)
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
            await self.bot.answer_callback_query(call.id, toast)

        def _make_subtask_command_handler(cmd, role, subtask):
            async def handler(message):
                logger.info("Command /%s received from %s", cmd, message.chat.id)
                week_num = datetime.date.today().isocalendar()[1]
                assignments = menage.get_role_assignments(colocataires)
                assigned_person = assignments.get(role, "?")
                role_data = chores.get_week_status().get(role, {})
                sub_data = role_data.get("subtasks", {}).get(subtask)
                text = _build_subtask_text(role, subtask, assigned_person, sub_data)
                keyboard = _build_subtask_keyboard(week_num, cmd, bool(sub_data))
                await self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
            return handler

        for cmd, (role, subtask) in menage.SUBTASK_COMMANDS.items():
            self.bot.message_handler(commands=[cmd])(
                _make_subtask_command_handler(cmd, role, subtask)
            )

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("subtask:"))
        async def handle_subtask_callback(call):
            parts = call.data.split(":")
            if len(parts) != 3:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return

            try:
                week_num = int(parts[1])
            except ValueError:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return
            cmd = parts[2]

            mapping = menage.SUBTASK_COMMANDS.get(cmd)
            if mapping is None:
                await self.bot.answer_callback_query(
                    call.id, "Sous-tâche inconnue.", show_alert=True,
                )
                return
            role, subtask = mapping

            current_week = datetime.date.today().isocalendar()[1]
            if week_num != current_week:
                await self.bot.answer_callback_query(
                    call.id, "Trop tard, c'est une autre semaine.", show_alert=True,
                )
                return

            user_id = call.from_user.id
            person = TELEGRAM_USER_MAP.get(user_id)
            if not person:
                await self.bot.answer_callback_query(
                    call.id, "Tu n'es pas reconnu.", show_alert=True,
                )
                return

            valid_subtasks = menage.get_subtasks_for_role(role)
            if valid_subtasks is None or subtask not in valid_subtasks:
                await self.bot.answer_callback_query(
                    call.id, "Sous-tâche inconnue.", show_alert=True,
                )
                return

            role_data = chores.get_week_status().get(role, {})
            existing = role_data.get("subtasks", {}).get(subtask)
            # Only the doer may untoggle. Open click to mark; restricted undo.
            if existing and existing.get("by") != person:
                await self.bot.answer_callback_query(
                    call.id,
                    f"Seul·e {existing['by']} peut annuler.",
                    show_alert=True,
                )
                return

            now_done = chores.toggle_subtask(role, subtask, person)
            toast = f"{subtask} fait !" if now_done else f"{subtask} annulé."

            assignments = menage.get_role_assignments(colocataires)
            assigned_person = assignments.get(role, "?")
            new_role_data = chores.get_week_status().get(role, {})
            new_sub_data = new_role_data.get("subtasks", {}).get(subtask)
            text = _build_subtask_text(role, subtask, assigned_person, new_sub_data)
            keyboard = _build_subtask_keyboard(week_num, cmd, bool(new_sub_data))
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
            await self.bot.answer_callback_query(call.id, toast)

        @self.bot.message_handler(commands=['cendrier'])
        async def send_cendrier(message):
            logger.info("Command /cendrier received from %s", message.chat.id)
            week_num = datetime.date.today().isocalendar()[1]
            state = cendrier.get_week_state()
            text = _build_cendrier_text(state)
            keyboard = _build_cendrier_keyboard(week_num, bool(state))
            await self.bot.send_message(message.chat.id, text, reply_markup=keyboard)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("cendrier:"))
        async def handle_cendrier_callback(call):
            parts = call.data.split(":")
            if len(parts) != 2:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return

            try:
                week_num = int(parts[1])
            except ValueError:
                await self.bot.answer_callback_query(call.id, "Données invalides.")
                return

            current_week = datetime.date.today().isocalendar()[1]
            if week_num != current_week:
                await self.bot.answer_callback_query(
                    call.id, "Trop tard, c'est une autre semaine.", show_alert=True,
                )
                return

            user_id = call.from_user.id
            person = TELEGRAM_USER_MAP.get(user_id)
            if not person:
                await self.bot.answer_callback_query(
                    call.id, "Tu n'es pas reconnu.", show_alert=True,
                )
                return

            existing = cendrier.get_week_state()
            # Only the doer may untoggle. Open click to mark; restricted undo.
            if existing and existing.get("by") != person:
                await self.bot.answer_callback_query(
                    call.id,
                    f"Seul·e {existing['by']} peut annuler.",
                    show_alert=True,
                )
                return

            new_state = cendrier.toggle_week_state(person)
            toast = "Cendrier vidé !" if new_state else "Annulé."

            text = _build_cendrier_text(new_state)
            keyboard = _build_cendrier_keyboard(week_num, bool(new_state))
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
            await self.bot.answer_callback_query(call.id, toast)

        @self.bot.message_handler(commands=['stats'])
        async def send_stats(message):
            logger.info("Command /stats received from %s", message.chat.id)
            if not self.dev_chat_id or str(message.chat.id) != self.dev_chat_id:
                logger.info("Ignoring /stats from non-dev chat %s", message.chat.id)
                return
            answer = chores.get_stats()
            await self.bot.send_message(message.chat.id, answer)
            logger.info("Sent stats answer")

        @self.bot.message_handler(regexp='jeremie?')
        async def jeremied(message):
            logger.info("Regexp 'jeremie?' matched by %s", message.chat.id)
            await self.bot.reply_to(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")
            logger.info("Replied with Jeremie's message")

    async def process_update(self, update_json):
        """Process a single update (for testing or Lambda)."""
        logger.info("Processing update: %s", update_json)
        update = telebot.types.Update.de_json(update_json)
        logger.info("Telebot deserialization succeeded")
        await self.bot.process_new_updates([update])
        logger.info("Update processed successfully")
