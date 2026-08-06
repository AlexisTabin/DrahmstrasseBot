import datetime
import logging
import random
from src.utils import is_even_week
from src import phrases

# Setup logging
logger = logging.getLogger(__name__)

ROLES = ["CUISINE", "SDBs", "SOLs", "DÉCHETS"]

# Chance that roles don't rotate this week — pure chaos/joke
CHAOS_KEEP_ROLES_PROBABILITY = 0.05

ROLE_SUBTASKS = {
    "CUISINE": ["frigo", "plan de travail", "rangement", "balcon"],
    "SDBs": ["petit WC", "grand WC", "lavabo", "baignoire", "Vider les petites poubelles"],
    "SOLs": ["aspirateur", "panosse"],
    "DÉCHETS": ["poubelle", "carton", "compost", "verre", "plastique"],
}
DECHETS_OPTIONAL_SUBTASK = "papier"

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
    "poubelle": ("DÉCHETS", "poubelle"),
    "compost": ("DÉCHETS", "compost"),
    "verre": ("DÉCHETS", "verre"),
    "plastique": ("DÉCHETS", "plastique"),
}


def get_subtasks_for_role(role):
    """Return the list of active sub-tasks for a role, or None for unknown roles."""
    subtasks = ROLE_SUBTASKS.get(role)
    if subtasks is None:
        return None
    result = list(subtasks)
    if role == "DÉCHETS" and is_even_week():
        result.append(DECHETS_OPTIONAL_SUBTASK)
    return result

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
Holiday redistribution
'''


def get_holiday_redistribution(
    role: str, absent_person: str, colocataires: list, holiday_people: set = None,
) -> dict:
    """Return {subtask: assignee} for `role`'s subtasks with `absent_person` away.

    Deterministic per (ISO week, role, absent_person) — like
    _should_keep_same_roles — so /vacances, /recap, and /reminder all agree
    without needing to persist the distribution itself; only the fact that
    `absent_person` is on holiday needs to be stored. Subtasks are shuffled
    then dealt round-robin across the remaining colocataires, so counts stay
    as equal as possible while which person gets which subtask is random.

    Anyone else currently in `holiday_people` is excluded from the candidate
    pool too — a subtask shouldn't land on someone who's also away. If that
    leaves no one eligible (e.g. everyone's on holiday), this returns {}: no
    one is expected to do it that week.

    `others` is sorted rather than left in `colocataires` order: different
    callers derive their colocataires list differently (e.g. chores.py uses
    role_assignments.values(), drahmbot.py uses its own fixed list) — same
    people, potentially different order. Sorting makes the result depend
    only on the *set* of remaining people, so every caller agrees.
    """
    subtasks = get_subtasks_for_role(role)
    if not subtasks:
        return {}
    holiday_people = holiday_people or set()
    others = sorted(
        p for p in colocataires if p != absent_person and p not in holiday_people
    )
    if not others:
        return {}
    iso = datetime.datetime.now().isocalendar()
    rng = random.Random(f"drahmbot-vacances-{iso[0]}-{iso[1]}-{role}-{absent_person}")
    shuffled = list(subtasks)
    rng.shuffle(shuffled)
    return {subtask: others[i % len(others)] for i, subtask in enumerate(shuffled)}


def get_effective_assignee(
    role: str, subtask: str, assigned_person: str, holiday_people: set, colocataires: list,
) -> str:
    """Return who is actually expected to do `subtask` of `role` this week.

    Falls back to `assigned_person` unchanged unless they're on holiday, in
    which case the deterministic redistribution takes over (or, if no one is
    eligible, `assigned_person` again — nothing to redistribute to).
    """
    if assigned_person not in holiday_people:
        return assigned_person
    redistribution = get_holiday_redistribution(
        role, assigned_person, colocataires, holiday_people,
    )
    return redistribution.get(subtask, assigned_person)


def get_effective_subtasks_for_person(
    person: str, role_assignments: dict, holiday_people: set, colocataires: list,
) -> list:
    """Return [(role, subtask), ...] for every subtask `person` is actually
    expected to do this week, across every role — not just their own
    nominal one. Used by /done, which used to only ever show a person's own
    role and so couldn't reflect holiday redistribution: a helper who
    inherited a subtask from a holidaying roommate couldn't mark it done via
    /done (only via the specific /frigo-style command), and someone on
    holiday would still see their own now-reassigned role as if nothing had
    changed.
    """
    pairs = []
    for role, assigned_person in role_assignments.items():
        subtasks = get_subtasks_for_role(role)
        if not subtasks:
            continue
        for subtask in subtasks:
            effective = get_effective_assignee(
                role, subtask, assigned_person, holiday_people, colocataires,
            )
            if effective == person:
                pairs.append((role, subtask))
    return pairs


'''
Get functions
'''

def getRoles(colocataires: list):
    assignments = get_role_assignments(colocataires)
    logger.info("Role assignments: %s", assignments)

    body = """
        ROLES DU MENAGES ATTRIBUÉS ALEATOIREMENT PAR LE DRAHMBOT    :
        - \U0001F373 CUISINE    : {}
        - \U0001F6BF SDBs       : {}
        - \U0001F9F9 SOLs       : {}
        - \U0001F5D1\uFE0F DÉCHETs     : {}
    """.format(
        assignments["CUISINE"],
        assignments["SDBs"],
        assignments["SOLs"],
        assignments["DÉCHETS"],
    )

    if _should_keep_same_roles():
        prefix = phrases.pick(phrases.MONDAY_SAME_ROLES)
    else:
        prefix = phrases.pick(phrases.MONDAY_NEW_ROLES)

    answer = prefix + "\n" + body
    logger.info("Assigned roles:\n%s", answer.strip())
    return answer


def get_papier_reminder(colocataires: list, holiday_people: set = None) -> str:
    """Papier reminder naming the responsible DÉCHETS person (or their
    holiday substitute, if the assigned person is away this week)."""
    assignments = get_role_assignments(colocataires)
    name = get_effective_assignee(
        "DÉCHETS", "papier", assignments["DÉCHETS"], holiday_people or set(), colocataires,
    )
    answer = f"{name} doit sortir le papier lundi"
    logger.info("Papier reminder: %s", answer)
    return answer


def get_carton_reminder(colocataires: list, holiday_people: set = None) -> str:
    """Carton reminder naming the responsible DÉCHETS person (or their
    holiday substitute, if the assigned person is away this week)."""
    assignments = get_role_assignments(colocataires)
    name = get_effective_assignee(
        "DÉCHETS", "carton", assignments["DÉCHETS"], holiday_people or set(), colocataires,
    )
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


