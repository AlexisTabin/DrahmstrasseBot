import datetime
import logging
from src.utils import is_even_week

# Setup logging
logger = logging.getLogger(__name__)

ROLES = ["CUISINE", "SDBs", "SOLs", "DÉCHETS"]

ROLE_SUBTASKS = {
    "CUISINE": ["frigo", "plan de travail", "rangement"],
    "SDBs": ["petit WC", "grand WC", "lavabo", "baignoire", "Vider les petites poubelles"],
    "SOLs": ["aspirateur", "panosse"],
    "DÉCHETS": ["poubelle", "carton", "compost", "verre", "plastique"],
}
DECHETS_OPTIONAL_SUBTASK = "papier"


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

def get_role_assignments(colocataires: list) -> dict:
    """Return a dict mapping role name to the assigned person for this week."""
    current_week_nb = datetime.datetime.now().isocalendar()[1] + 1
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

    answer = """
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


def getCartonOrPapier(colocataires: list) -> str:
    """Show the new papier/carton schedule and responsible person."""
    assignments = get_role_assignments(colocataires)
    name = assignments["DÉCHETS"]
    answer = (
        "Nouveau calendrier :\n"
        "- Papier : tous les lundis soir\n"
        "- Carton : tous les mercredis soir\n"
        f"Cette semaine, c'est {name} (DÉCHETS) qui s'en occupe !"
    )
    logger.info("Carton/Papier info: %s", answer)
    return answer


def getCarteDeLessive():
    answer = """Pour commander une carte ou un badge, veuillez consulter le site internet
https://www.lavorent.ch/fr/product/hyperion-100/

et lâcher 100 balles
    """
    logger.info("Returning lessive card info")
    return answer


'''
For schedulers
'''

def changeRoles(colocataires: list):
    answer = getRoles(colocataires)

    if is_even_week():
        answer = "Encore une semaine avec les mêmes rôles ehehe\n" + answer
    else:
        answer = "Coucou, changement de rôles pour le ménage ehehe\n" + answer

    logger.info("ChangeRoles message:\n%s", answer.strip())
    return answer
