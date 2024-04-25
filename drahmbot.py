import csv
import datetime
import time
from random import randrange

import requests
import yaml
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch

import telepot
from avent import get_avent_calendar_msg, getCadeaux, getCadeauxPlannning
from chenil import getQuote, getRap
from menage import getCartonOrPapier, getRoles
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

LEA = 'Lea'
TIMON = 'timon'
MAEL = 'Maël'
ALEXIS = 'Alexis'

# read token from yml file
with open("bot_token.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, yaml.FullLoader)
    # get token from yml file
    token = cfg['telegram_bot_token']

    DRAHMSTRASSE_GROUP_ID = cfg['bot_chat_id']
    ALEXIS_ID = cfg['alexis_id']
    LEA_ID = ['lea_id']
#chat_id = DRAHMSTRASSE_GROUP_ID
    

max_poet = 0
def on_callback_query(msg):
    global max_poet
    print("msg received : ", msg)
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    print('Callback Query :', query_id, from_id, query_data)
    print('Max poet : ', max_poet)
    if max_poet < 1:
        bot.answerCallbackQuery(query_id, text='POÊÊÊÊÊÊÊÊÊÊÊÊT')
        bot.sendMessage(chat_id, 'POÊÊÊÊÊÊÊÊÊÊÊÊT')
        max_poet += 2
    else :
        bot.answerCallbackQuery(query_id, text='Maximum POET reached, please stop')
        max_poet -= 0.1
    

    
def handle(msg):
    global chat_id
    print("Message received: " + str(msg))
    try:

        
        chat_id = msg['chat']['id']

        # handle the case where the message doesn't have the key 'text'
        if 'text' not in msg:
            if 'caption' in msg:
                command = msg['caption']
            else:
                command = ""
                return bot.sendMessage(chat_id, "Je ne comprends pas ce message :(")
        else:
            command = msg['text']

        print('Got command: %s' % command)

        # if command contains an @ remvoe it and what comes after
        if '@' in command:
            command = command.split('@')[0]
            print('Updated command: %s' % command)

        if command == '/roles':
            answer = getRoles(colocataires=[LEA, MAEL, TIMON, ALEXIS])
            bot.sendMessage(chat_id, answer)

        elif command == '/papier' or command == '/carton':
            papierOrCarton = getCartonOrPapier()
            answer = "C'est le {} qui est à sortir cette semaine !".format(
                papierOrCarton)
            bot.sendMessage(chat_id, answer)

        elif command == '/time':
            msg = getCadeaux(msg)
            bot.sendMessage(chat_id, msg)

        elif command == '/avent':
            # if we are still not in december, print the number of days left
            if datetime.datetime.now().month != 12:
                answer = "Il reste {} jours avant le début de l'Avent !".format(
                    (datetime.datetime(2023, 12, 1) - datetime.datetime.now()).days)
            else:
                answer = "C'est l'Avent !\n\n"
                answer = answer + get_avent_calendar_msg()
            bot.sendMessage(chat_id, answer)

        elif command == '/rendu':
            # print number of days left before the 15th of december
            nbr_jours_restant_timon = (datetime.datetime(
                2023, 12, 15) - datetime.datetime.now()).days
            # answer = "Timon, il te reste {} jours avant ton rendu !".format((datetime.datetime(2023, 12, 15) - datetime.datetime.now()).days)
            answer = "Timon, ne t'inquiète pas, tu as encore le temps !" if nbr_jours_restant_timon > 7 else "OULA Timon, il est temps de rendre ton projet !"
            answer = answer + "\n\n" + "Alexis, il te reste {} jours avant ton rendu !".format(
                (datetime.datetime(2024, 4, 15) - datetime.datetime.now()).days)
            bot.sendMessage(chat_id, answer)

        elif command == 'POET' or command == 'POÊT':
            content_type, chat_type, chat_id = telepot.glance(msg)
            print("content type : ", content_type)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Press me', callback_data='press')],
                ])
            bot.sendMessage(chat_id, 'POET ?', reply_markup=keyboard)

        elif command == '/quote':
            bot.sendMessage(chat_id, getQuote())

        elif command == '/yoga':
            yogas = [
                'https://youtu.be/v7AYKMP6rOE', 'https://youtu.be/UHGLQUUuTeM',
                'https://youtu.be/AYdQUS7jfPA', 'https://youtu.be/DvJa9tiMivw',
                'https://youtu.be/5X5p2hXlosk', 'https://youtu.be/uxp5xb7Sdo8',
                'https://youtu.be/TSIbzfcnv_8', 'https://youtu.be/ihba9Lw0tv4',
                'https://youtu.be/LqXZ628YNj4', 'https://youtu.be/VUnaqOANaY8',
                'https://youtu.be/dxoY1i6alSk',
                'https://youtu.be/6XM-Jzq-pOA', 'https://youtu.be/velPc7_mFsk'
            ]
            bot.sendMessage(chat_id, yogas[randrange(1, len(yogas))])

        elif command == '/physio':
            physio = [
                'https://www.youtube.com/watch?v=2eA2Koq6pTI&pp=ygUOYmFjayBwYWluIHlvZ2E%3D',
                'https://www.youtube.com/watch?v=XeXz8fIZDCE&pp=ygUOYmFjayBwYWluIHlvZ2E%3D',
                'https://www.youtube.com/watch?v=HzXkMnvqojE&pp=ygUOYmFjayBwYWluIHlvZ2E%3D'
            ]
            bot.sendMessage(chat_id, physio[randrange(1, len(physio))])

        elif command == '/rap':
            answer = getRap()
            bot.sendMessage(chat_id, answer)

        elif command == 'youpie' or command == 'Youpie':
            bot.sendMessage(chat_id, 'Youpiiiiiiiiiiiiiiie!')

        elif command == '/lessive':
            addresse = "LAVORENT\nBernstrasse 60\n8952 Schlieren"
            conditions = "Les cartes et badges rechargeables font l\'objet d\'une caution.\nCelle-ci est remboursée à la demande de l\'utilisateur.\nElle lui sera rendue par virement bancaire à réception de ladite carte ou badge au bureau de vente LAVORENT SA dans une enveloppe matelassée."
            commande = "Pour commander une carte ou un badge, veuillez consulter le site internet https://www.lavorent.ch/fr/product/hyperion-100/"
            message = conditions + "\n\n" + addresse + "\n\n" + commande
            bot.sendMessage(chat_id, message)

        elif command == '/cadeaux':
            msg = getCadeaux(msg)
            bot.sendMessage(chat_id, msg)

        elif command == '/help':
            answer = "Voici la liste des commandes que je comprends :\n"
            # read from commands.txt
            with open('commands.txt', 'r') as f:
                answer = answer + f.read()

            bot.sendMessage(chat_id, answer)

        # we want to know which day the gifter has to give a gift to the receiver
        elif command == '/cadeaux_planning':
            msg = getCadeauxPlannning(msg)
            bot.sendMessage(chat_id, msg)

        elif command == '/avent_planning':
            answer = "Voici le planning de l'Avent :\n\n"
            # read from commands.txt
            with open('avent_calendar.csv', 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                calendar = list(reader)

            for day in calendar:
                answer += "Le {} décembre : {} offre un cadeau à {}\n".format(
                    day['day'], day['gifter'], day['receiver'])

            bot.sendMessage(chat_id, answer)

    except Exception as e:
        print("Exception occured: " + str(e))
        answer = "Je ne comprends pas ce message :("
        answer = answer + "\n\n" + "Exception: " + str(e)
        bot.sendMessage(chat_id, answer)


bot = telepot.Bot(token)

MessageLoop(bot, {'chat': handle,
                  'callback_query' : on_callback_query
    }).run_as_thread()
print('I am listening ...')

while 1:
    try:
        # if time of the day is 11:45 am send a message to the group telling the time of the day and to have a nice day
        # send only on the 24th of February
        if datetime.datetime.now().hour == 11 and datetime.datetime.now().minute == 45 and datetime.datetime.now().day == 24 and datetime.datetime.now().month == 2:
            print("It's 11:45 am, time to send a message to the group !")
            bot.sendMessage(
                LEA_ID, "YO Léa\n ÇA JOUE ? N'oublie pas qu'il est 11h45, il est temps de faire la pause !\nBon appétit et bonne journéeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee !")
            bot.sendMessage(
                LEA_ID, "Héhéhé, tu as cru que j'allais oublier ?\nBon appétit et bonne journé")
            bot.sendMessage(
                LEA_ID, "Sur ce, je te laisse, je vais faire une sieste !")
            bot.sendMessage(
                ALEXIS_ID, "YO Léa\n ÇA JOUE ? N'oublie pas qu'il est 11h45, il est temps de faire la pause !\nBon appétit et bonne journéeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee !")
            bot.sendMessage(
                ALEXIS_ID, "Héhéhé, tu as cru que j'allais oublier ?\nBon appétit et bonne journé")
            bot.sendMessage(
                ALEXIS_ID, "Sur ce, je te laisse, je vais faire une sieste !")
            time.sleep(60)

        if datetime.datetime.now().hour == 23 and datetime.datetime.now().minute == 00:
            print("It's 23:00 pm, time to send a message to Alexis !")
            bot.sendMessage(
                ALEXIS_ID, "Il est 23h00, il est temps d'éteindre tes écrans et d'aller te coucher Alexis !")
            time.sleep(60)

        # Each 2 weeks, change roles
        is_changing_week = datetime.datetime.now().isocalendar()[1] % 2 == 1
        is_monday_morning = is_changing_week and datetime.datetime.now().isocalendar(
        )[2] == 1 and datetime.datetime.now().hour == 12 and datetime.datetime.now().minute == 5
        # print("Is changing week: " + str(is_changing_week))
        # print("Is monday morning: " + str(is_monday_morning))
        if is_monday_morning:
            print("It's monday morning, time to change roles !")
            answer = getRoles()
            answer = "Coucou Timon, Maël, Léa et Alexis !\n\n C'est lundi, il est midi, c'est l'heure de changer les rôles !\n" + \
                answer + "\n\nBonne semaine à tous !"
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, answer)
            time.sleep(60)

        # Each monday evening, send a message to say to not forget to take out the paper or the carton
        is_monday_evening = datetime.datetime.now().isocalendar(
        )[2] == 1 and datetime.datetime.now().hour == 18 and datetime.datetime.now().minute == 0
        if is_monday_evening:
            papierOrCarton = getCartonOrPapier()
            answer = "Coucou tout le monde !\n\nC'est lundi soir, n'oubliez pas de sortir le {} pour qu'il soit rammassé demain matin !".format(
                papierOrCarton)
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, answer)
            time.sleep(60)

        # For each day of the Avent, send a message to the group to say who is the gifter and who is the receiver
        is_advent = datetime.datetime.now().month == 12
        is_advent_day = datetime.datetime.now().day <= 24
        is_advent_day_morning = is_advent and is_advent_day and datetime.datetime.now(
        ).hour == 7 and datetime.datetime.now().minute == 30
        if is_advent_day_morning:
            print("It's advent day morning, time to send a message to the group !")
            answer = get_avent_calendar_msg()
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, answer)
            time.sleep(60)

        time.sleep(10)

    except Exception as e:
        time.sleep(60)
        print("Exception occured: " + str(e))
        # answer = "Je ne comprends pas ce message :("
        # answer = answer + "\n\n" + "Exception: " + str(e)
        # bot.sendMessage(ALEXIS_ID, answer)
