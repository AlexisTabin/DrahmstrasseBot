import time
import random
import datetime
import telepot
import yaml
from telepot.loop import MessageLoop

"""
This is a simple bot that listens to two commands:
"""

LEA = 'LEA'
TIMON = 'TIMON'
MAEL = 'MAEUL'
ALEXIS = 'ALEXIS'

def handle(msg):
    print("Message received: " + str(msg))
    chat_id = msg['chat']['id']
    command = msg['text']

    print('Got command: %s' % command)

    # if command contains an @ remvoe it and what comes after
    if '@' in command:
        command = command.split('@')[0]
        print('Updated command: %s' % command)

    if command == '/roles':
        inital_week_nb = datetime.date(2023, 10, 9).isocalendar()[1]

        print("initial week nb: " + str(inital_week_nb))
        print("current week nb: " + str(datetime.datetime.now().isocalendar()[1]))
        # increment index by 1 every 2 weeks
        index = (datetime.datetime.now().isocalendar()[1] - inital_week_nb) // 2
        print("index: " + str(index))
        if index == 1 :
            roles = [LEA, ALEXIS, TIMON, MAEL]
        else:
            roles = [LEA, MAEL , TIMON, ALEXIS]

        answer = """
            ROLES DU MENAGES ATTRIBUÉS ALEATOIREMENT PAR LE DRAHMBOT    : 
            - CUISINE    : {}
            - SOLS         : {}
            - SDBs         : {}
            - DÉCHET   : {}
        """.format(roles[(index + 0) % 4], roles[(index + 1) % 4], roles[(index + 2) % 4], roles[(index + 3) % 4])
        bot.sendMessage(chat_id, answer)
    elif command == '/papier' or command == '/carton':
        # if current week is even then it's Carton else it's Papier
        if datetime.datetime.now().isocalendar()[1] % 2 == 0:
            answer = "C'est la semaine du Carton !"
        else:
            answer = "C'est la semaine du Papier !"
        bot.sendMessage(chat_id, answer)
    elif command == '/time':
        bot.sendMessage(chat_id, str(datetime.datetime.now()))

# read token from yml file
with open("bot_token.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
    token = cfg['telegram_bot_token']

bot = telepot.Bot(token)

MessageLoop(bot, handle).run_as_thread()
print('I am listening ...')

while 1:
    time.sleep(10)
