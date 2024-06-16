import csv
import datetime
from random import randrange


'''
get functions
'''

def getRoles(colocataires: list):
    inital_week_nb = datetime.date(2023, 10, 9).isocalendar()[1]

    print("initial week nb: " + str(inital_week_nb))
    print("current week nb: " + str(datetime.datetime.now().isocalendar()[1]))
    # increment index by 1 every 2 weeks
    index = (datetime.datetime.now().isocalendar()[1] - inital_week_nb) // 2

    answer = """
            ROLES DU MENAGES ATTRIBUÉS ALEATOIREMENT PAR LE DRAHMBOT    : 
            - CUISINE    : {}
            - SOLS         : {}
            - SDBs         : {}
            - DÉCHET   : {}
        """.format(colocataires[(index + 0) % 4], colocataires[(index + 1) % 4], colocataires[(index + 2) % 4], colocataires[(index + 3) % 4])
    return answer


def getCartonOrPapier():
    # if current week is even then it's Carton else it's Papier
    if datetime.datetime.now().isocalendar()[1] % 2 == 0:
        answer = "N'est-il pas que c'est le papier cette semaine!"
    else:
        answer = "Cette semaine, c'est le carton qui est la star!"
    return answer

def getCarteDeLessive():
    answer = "Pour commander une carte ou un badge, veuillez consulter le site internet https://www.lavorent.ch/fr/product/hyperion-100/"
    return answer


'''
For schedulers
'''

