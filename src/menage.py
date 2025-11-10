import datetime
import logging
from src.utils import is_even_week

# Setup logging
logger = logging.getLogger(__name__)

'''
Get functions
'''

def getRoles(colocataires: list):
    current_week_nb = datetime.datetime.now().isocalendar()[1] + 1
    logger.info("Calculated role index shift: %d", current_week_nb)

    answer = """
        ROLES DU MENAGES ATTRIBUÉS ALEATOIREMENT PAR LE DRAHMBOT    : 
        - CUISINE    : {}
        - SDBs       : {}
        - SOLs       : {}
        - DÉCHETs     : {}
        *NEW* Le rôle de la cuisine englobe le salon aussi :)
    """.format(
        colocataires[(current_week_nb + 0) % 4],
        colocataires[(current_week_nb + 1) % 4],
        colocataires[(current_week_nb + 2) % 4],
        colocataires[(current_week_nb + 3) % 4]
    )

    logger.info("Assigned roles:\n%s", answer.strip())
    return answer

def getCartonOrPapier():
    if is_even_week():
        answer = "N'est-il pas que c'est le papier cette semaine!"
    else:
        answer = "Cette semaine, c'est le carton qui est la star!"
    logger.info("Carton/Papier decision: %s", answer)
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

