import datetime
import logging
from src.utils import is_even_week

# Setup logging
logger = logging.getLogger(__name__)

ROLES = ["CUISINE", "SDBs", "SOLs", "DÉCHETS"]

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
        - CUISINE    : {}
        - SDBs       : {}
        - SOLs       : {}
        - DÉCHETS (papier + carton) : {}
        *NEW* Le rôle de la cuisine englobe le salon aussi :)
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
    answer = f"Rappel papier ! {name}, c'est toi qui gère le papier ce soir. 📦"
    logger.info("Papier reminder: %s", answer)
    return answer


def get_carton_reminder(colocataires: list) -> str:
    """Carton reminder naming the responsible DÉCHETS person."""
    assignments = get_role_assignments(colocataires)
    name = assignments["DÉCHETS"]
    answer = f"Rappel carton ! {name}, c'est toi qui gère le carton ce soir. 📦"
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
