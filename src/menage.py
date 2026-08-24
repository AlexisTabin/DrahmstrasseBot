import datetime
import logging
import random
from src.utils import is_even_week
from src import phrases

# Setup logging
logger = logging.getLogger(__name__)

ROLES = ["CUISINE", "SDBs", "SOLs", "DÉCHETS"]

ROLE_EMOJIS = {
    "CUISINE": "\U0001F373",
    "SDBs": "\U0001F6BF",
    "SOLs": "\U0001F9F9",
    "DÉCHETS": "\U0001F5D1️",
}

# Chance that roles don't rotate this week — pure chaos/joke
CHAOS_KEEP_ROLES_PROBABILITY = 0.05

ROLE_SUBTASKS = {
    "CUISINE": ["frigo", "plan de travail", "rangement", "balcon", "lave-vaisselle"],
    "SDBs": ["petit WC", "grand WC", "lavabo", "baignoire", "Vider les petites poubelles"],
    "SOLs": ["aspirateur", "panosse"],
    "DÉCHETS": ["poubelle", "carton", "compost", "verre", "plastique"],
}
# Only part of DÉCHETS on even weeks, but required like any other subtask then
# (unlike OPTIONAL_SUBTASKS below, which never count towards completion).
DECHETS_EVEN_WEEK_SUBTASK = "papier"

# Sub-tasks attached to a role for visibility, but which nobody is ever on the
# hook for: they show up on the role's /done card and earn stats credit, yet
# /recap and /reminder never hold the role's assignee to them (see
# get_required_subtasks_for_role). Anyone can tick them, whatever their role.
OPTIONAL_SUBTASKS = {
    ("CUISINE", "lave-vaisselle"),
}

# Sub-tasks that can legitimately be done more than once in the same week
# (e.g. wiping the counter after every use) get a per-week counter instead of
# a done/not-done toggle. Counting as the role's completion requirement is
# still satisfied as soon as the counter is >= 1, same as any other subtask.
COUNTER_SUBTASKS = {
    ("CUISINE", "plan de travail"),
    ("CUISINE", "lave-vaisselle"),
}

# Maps a Telegram command name to the (role, subtask) it marks as done, so
# anyone can call e.g. /frigo to record a subtask even if it isn't their role
# this week. papier/carton are excluded: they already have dedicated
# commands (/papier, /carton) with their own reminder text.
SUBTASK_COMMANDS = {
    "frigo": ("CUISINE", "frigo"),
    "plandetravail": ("CUISINE", "plan de travail"),
    "rangement": ("CUISINE", "rangement"),
    "balcon": ("CUISINE", "balcon"),
    "petitwc": ("SDBs", "petit WC"),
    "grandwc": ("SDBs", "grand WC"),
    "lavabo": ("SDBs", "lavabo"),
    "baignoire": ("SDBs", "baignoire"),
    "poubelles": ("SDBs", "Vider les petites poubelles"),
    "aspirateur": ("SOLs", "aspirateur"),
    "panosse": ("SOLs", "panosse"),
    "lavevaisselle": ("CUISINE", "lave-vaisselle"),
    "poubelle": ("DÉCHETS", "poubelle"),
    "compost": ("DÉCHETS", "compost"),
    "verre": ("DÉCHETS", "verre"),
    "plastique": ("DÉCHETS", "plastique"),
}


def is_counter_subtask(role, subtask) -> bool:
    """Whether a (role, subtask) pair uses a repeat counter instead of a toggle."""
    return (role, subtask) in COUNTER_SUBTASKS


def is_optional_subtask(role, subtask) -> bool:
    """Whether a (role, subtask) pair is a bonus that never blocks the role."""
    return (role, subtask) in OPTIONAL_SUBTASKS


def get_subtasks_for_role(role):
    """Return the list of active sub-tasks for a role, or None for unknown roles.

    Includes the optional ones (OPTIONAL_SUBTASKS): this is the display and
    "is this subtask real?" list. Completion checks want
    get_required_subtasks_for_role instead.
    """
    subtasks = ROLE_SUBTASKS.get(role)
    if subtasks is None:
        return None
    result = list(subtasks)
    if role == "DÉCHETS" and is_even_week():
        result.append(DECHETS_EVEN_WEEK_SUBTASK)
    return result


def get_optional_subtasks_for_role(role):
    """Return this role's optional sub-tasks, in ROLE_SUBTASKS order."""
    subtasks = get_subtasks_for_role(role)
    if subtasks is None:
        return []
    return [s for s in subtasks if is_optional_subtask(role, s)]


def get_required_subtasks_for_role(role):
    """Return the sub-tasks a role must all have done to count as complete,
    i.e. its active list minus the optional extras. None for unknown roles."""
    subtasks = get_subtasks_for_role(role)
    if subtasks is None:
        return None
    return [s for s in subtasks if not is_optional_subtask(role, s)]

'''
Role computation
'''

def _should_keep_same_roles() -> bool:
    """Deterministic per ISO week — True ~5% of the time as a playful prank."""
    iso = datetime.datetime.now().isocalendar()
    rng = random.Random(f"drahmbot-roles-{iso[0]}-{iso[1]}")
    return rng.random() < CHAOS_KEEP_ROLES_PROBABILITY


def get_role_assignments(colocataires: list) -> dict:
    """Return a dict mapping role name to the assigned person for this week.

    Normally rotates by +1 each week; on a chaos week (~5% chance, deterministic
    per ISO week) the shift stays at last week's value so everyone keeps their
    role.
    """
    current_week_nb = datetime.datetime.now().isocalendar()[1] + 1
    if _should_keep_same_roles():
        current_week_nb -= 1
    logger.info("Calculated role index shift: %d", current_week_nb)
    return {
        role: colocataires[(current_week_nb + i) % len(colocataires)]
        for i, role in enumerate(ROLES)
    }


def get_role_for_person(colocataires: list, person: str):
    """Return the role assigned to a person this week, or None."""
    assignments = get_role_assignments(colocataires)
    for role, assigned in assignments.items():
        if assigned == person:
            return role
    return None


'''
Get functions
'''

def getRoles(colocataires: list):
    assignments = get_role_assignments(colocataires)
    logger.info("Role assignments: %s", assignments)

    body = """
        ROLES DU MENAGES ATTRIBUÉS ALEATOIREMENT PAR LE DRAHMBOT    :
        - {cuisine_emoji} CUISINE    : {cuisine}
        - {sdbs_emoji} SDBs       : {sdbs}
        - {sols_emoji} SOLs       : {sols}
        - {dechets_emoji} DÉCHETs     : {dechets}
    """.format(
        cuisine_emoji=ROLE_EMOJIS["CUISINE"], cuisine=assignments["CUISINE"],
        sdbs_emoji=ROLE_EMOJIS["SDBs"], sdbs=assignments["SDBs"],
        sols_emoji=ROLE_EMOJIS["SOLs"], sols=assignments["SOLs"],
        dechets_emoji=ROLE_EMOJIS["DÉCHETS"], dechets=assignments["DÉCHETS"],
    )

    if _should_keep_same_roles():
        prefix = phrases.pick(phrases.MONDAY_SAME_ROLES)
    else:
        prefix = phrases.pick(phrases.MONDAY_NEW_ROLES)

    answer = prefix + "\n" + body
    logger.info("Assigned roles:\n%s", answer.strip())
    return answer


def get_papier_reminder(colocataires: list) -> str:
    """Papier reminder naming the responsible DÉCHETS person."""
    assignments = get_role_assignments(colocataires)
    name = assignments["DÉCHETS"]
    answer = f"{name} doit sortir le papier lundi"
    logger.info("Papier reminder: %s", answer)
    return answer


def get_carton_reminder(colocataires: list) -> str:
    """Carton reminder naming the responsible DÉCHETS person."""
    assignments = get_role_assignments(colocataires)
    name = assignments["DÉCHETS"]
    answer = f"{name} doit sortir le carton mercredi"
    logger.info("Carton reminder: %s", answer)
    return answer


def getCarteDeLessive():
    answer = """Pour commander une carte ou un badge, veuillez consulter le site internet
https://www.lavorent.ch/fr/product/hyperion-100/

et lâcher 100 balles
    """
    logger.info("Returning lessive card info")
    return answer


