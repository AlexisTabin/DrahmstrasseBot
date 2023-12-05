import time
import random
import datetime
import telepot
import yaml
from telepot.loop import MessageLoop
import csv
import requests
from bs4 import BeautifulSoup
from random import randrange
from youtubesearchpython import VideosSearch


LEA = 'Lea'
TIMON = 'timon'
MAEL = 'Maël'
ALEXIS = 'Alexis'
DRAHMSTRASSE_GROUP_ID = -1001633433047
ALEXIS_ID = 891406979

def getQuote():
        url = 'https://quotes.toscrape.com/'
        HEADERS = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')

        quotes = soup.find_all("div", attrs={'class':'quote'})
        print(quotes)
        q = quotes[randrange(len(quotes))]
        q_text = q.find("span", attrs={'class':'text'}).text
        print("q_text: " + str(q_text))
        print("--------------------"*10)
        print("Q again : " + str(q))
        q_author_tag = q.find("small", attrs={'class':'author'})
        print("q_author_tag: " + str(q_author_tag))
        q_author = q_author_tag.text if q_author_tag else "Unknown Author"
            
        fmt_text = "{} ~ {}".format(q_text, q_author)

        return fmt_text

def getRap():
    url = 'https://www.lymu.net/punchlines-citations-rap'
    HEADERS = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    artists = soup.find_all("span", attrs={'class':'StylableButton2545352419__label wixui-button__label'})
    artists = [str(a.text).split(" ")[-1] for a in artists if a.text != "Connexion"]
    artist = artists[randrange(len(artists))]
    print("artist: " + str(artist))


    if artist == "Ninho":
        artist_url = "https://www.lymu.net/punchlines-ninho"

    else:
        artist_url = "https://www.lymu.net/{}-punchlines".format(str(artist).lower())

    artist_r = requests.get(artist_url, headers=HEADERS)
    artist_soup = BeautifulSoup(artist_r.text, 'html.parser')
    quotes = artist_soup.find_all("span", attrs={'class':'color_14 wixui-rich-text__text'})
    # if artist == "Ninho":
    #     quote = quotes[randrange(len(quotes))]
    #     return quote.text + "\n- " + artist + "\n" + "https://www.youtube.com/watch?v=3BI1K6oXTqQ"
    # if artist == "Niska":
    #     quote = quotes[randrange(len(quotes))]
    #     return quote.text + "\n- " + artist + "\n" + "https://www.youtube.com/watch?v=GaYNpipK8hg"
    
    if artist in ["Damso", "Ninho", "Niska"]:
        albums = artist_soup.find_all("span", attrs={'class':'color_15 wixui-rich-text__text'})
        albums = [str(a.text).split(' ')[-1] for a in albums[2:] if '-' in a.text]
        links = [VideosSearch(artist + ' ' + album, limit = 1) for album in albums]
        links = [l.result()['result'][0]['link'] for l in links]
        index = randrange(min(len(links), len(quotes))) if (len(links) != len(quotes)) else randrange(len(quotes))
        quote = quotes[index]
        link = links[index]
   
        return quote.text + "\n- " + artist + "\n" + link
    else :
        links = artist_soup.find_all("a", attrs={'class':'wixui-rich-text__text'})
        links = [l for l in links if "youtube" in l['href']]
        index = randrange(min(len(links), len(quotes))) if (len(links) != len(quotes)) else randrange(len(quotes))
        quote = quotes[index]
        link = links[index]
    
        return quote.text + "\n- " + artist + "\n" + link['href']

def get_avent_calendar_msg():
    
    # Read avent_calendar.csv using the csv library
    with open('avent_calendar.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        calendar = list(reader)

    # Get the current day
    day = datetime.datetime.now().day

    # Ensure day is between 1 and 24
    if day < 1 or day > 24:
        return "Ce n'est plus l'Avent ! :("

    # Get the current day's gifter and receiver from the csv data
    gifter = calendar[day - 1]['gifter']
    receiver = calendar[day - 1]['receiver']

    if day == 1:
        day = "1er"
    
    answer = "En cette belle journée du {} Décembre, c'est au tour de {} d'offrir un cadeau à {} !".format(day, gifter, receiver)
    return answer

def getCadeaux(msg):
    msg_from = msg['from']['first_name']
    answer = "{}, voici les cadeaux que tu dois offir :\n".format(msg_from)
    
    # Read avent_calendar.csv using the csv library
    with open('avent_calendar.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        calendar = list(reader)
     # Count the number of gifts given by each person
    gifts_given = {}

    for day in calendar:
        gifter = day['gifter']
        receiver = day['receiver']
        
        gifts_given[(gifter, receiver)] = gifts_given.get((gifter, receiver), 0) + 1

    # Display the results
    for (gifter, receiver), count in gifts_given.items():
        offer = f"{count} cadeaux à {receiver}"
        if msg_from in gifter:
            answer = answer + "\n" + offer

    return answer

def getRoles():
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
        return answer

def getCartonOrPapier():
    # if current week is even then it's Carton else it's Papier
    if datetime.datetime.now().isocalendar()[1] % 2 == 0:
        answer = "papier"
    else:
        answer = "carton"
    return answer

def getCadeauxPlannning(msg):
    msg_from = msg['from']['first_name']
    answer = "{}, voici quand et à qui tu dois offrir les cadeaux :\n".format(msg_from)
    
    # Read avent_calendar.csv using the csv library
    with open('avent_calendar.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        calendar = list(reader)

     # Count the number of gifts given by each person
    gifts_given = {}

    for day in calendar:
        if int(day['day']) == 22:
            print("Day : " + str(day))
            print("Gifter : " + str(day['gifter']))
            print("Receiver : " + str(day['receiver']))
        if msg_from in  day['gifter']:
            receiver = day['receiver']
            date = day['day']
            answer += "\nLe " + (date if int(date) != 1 else '1er') + " décembre pour " + receiver + "."

    answer += "\n\nBonne chance !"
    return answer

def handle(msg):
    print("Message received: " + str(msg))
    try : 
        chat_id = msg['chat']['id']
        # handle the case where the message doesn't have the key 'text'
        if 'text' not in msg:
            if 'caption' in msg:
                command = msg['caption']
            else :
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
            answer = getRoles()
            bot.sendMessage(chat_id, answer)

        elif command == '/papier' or command == '/carton':
            papierOrCarton = getCartonOrPapier()
            answer = "C'est le {} qui est à sortir cette semaine !".format(papierOrCarton)
            bot.sendMessage(chat_id, answer)

        elif command == '/time':
            msg = getCadeaux(msg)
            bot.sendMessage(chat_id, msg)

        elif command == '/avent':
            # if we are still not in december, print the number of days left
            if datetime.datetime.now().month != 12:
                answer = "Il reste {} jours avant le début de l'Avent !".format((datetime.datetime(2023, 12, 1) - datetime.datetime.now()).days)
            else:
                answer = "C'est l'Avent !\n\n"
                answer = answer + get_avent_calendar_msg()
            bot.sendMessage(chat_id, answer)

        elif command == '/rendu':
            # print number of days left before the 15th of december
            nbr_jours_restant_timon = (datetime.datetime(2023, 12, 15) - datetime.datetime.now()).days
            # answer = "Timon, il te reste {} jours avant ton rendu !".format((datetime.datetime(2023, 12, 15) - datetime.datetime.now()).days)
            answer = "Timon, ne t'inquiète pas, tu as encore le temps !" if nbr_jours_restant_timon > 7 else "OULA Timon, il est temps de rendre ton projet !"
            answer = answer + "\n\n" + "Alexis, il te reste {} jours avant ton rendu !".format((datetime.datetime(2024, 4, 15) - datetime.datetime.now()).days)
            bot.sendMessage(chat_id, answer)

        elif command == 'POET' or command == 'POÊT':
            bot.sendMessage(chat_id, 'POÊÊÊÊÊÊÊÊÊÊÊÊT')

        elif command == '/quote':
            bot.sendMessage(chat_id, getQuote())

        elif command == '/yoga':
            yogas = [
                'https://youtu.be/v7AYKMP6rOE','https://youtu.be/UHGLQUUuTeM',
                'https://youtu.be/AYdQUS7jfPA','https://youtu.be/DvJa9tiMivw',
                'https://youtu.be/5X5p2hXlosk','https://youtu.be/uxp5xb7Sdo8',
                'https://youtu.be/TSIbzfcnv_8','https://youtu.be/ihba9Lw0tv4',
                'https://youtu.be/LqXZ628YNj4','https://youtu.be/VUnaqOANaY8',
                'https://youtu.be/dxoY1i6alSk',
                'https://youtu.be/6XM-Jzq-pOA','https://youtu.be/velPc7_mFsk'
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
                answer += "Le {} décembre : {} offre un cadeau à {}\n".format(day['day'], day['gifter'], day['receiver'])
                
            bot.sendMessage(chat_id, answer)
            

    except Exception as e:
        print("Exception occured: " + str(e))
        answer = "Je ne comprends pas ce message :("
        answer = answer + "\n\n" + "Exception: " + str(e)
        bot.sendMessage(chat_id, answer)

# read token from yml file
with open("bot_token.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, yaml.FullLoader)
    # get token from yml file 
    token = cfg['telegram_bot_token']

bot = telepot.Bot(token)

MessageLoop(bot, handle).run_as_thread()
print('I am listening ...')

while 1:
    try : 
        # if time of the day is 11:45 am send a message to the group telling the time of the day and to have a nice day
        if datetime.datetime.now().hour == 11 and datetime.datetime.now().minute == 45:
            print("It's 11:45 am, time to send a message to the group !")
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, "Il est 11h45, il est temps de faire la pause !\nBon appétit et bonne journée !")
            time.sleep(60)

        if datetime.datetime.now().hour == 23 and datetime.datetime.now().minute == 00:
            print("It's 23:00 pm, time to send a message to Alexis !")
            bot.sendMessage(ALEXIS_ID, "Il est 23h00, il est temps d'éteindre tes écrans et d'aller te coucher Alexis !")
            time.sleep(60)
            
        # Each 2 weeks, change roles
        is_changing_week = datetime.datetime.now().isocalendar()[1] % 2 == 1
        is_monday_morning = is_changing_week and datetime.datetime.now().isocalendar()[2] == 1 and datetime.datetime.now().hour == 12 and datetime.datetime.now().minute == 5
        # print("Is changing week: " + str(is_changing_week))
        # print("Is monday morning: " + str(is_monday_morning))
        if is_monday_morning:
            print("It's monday morning, time to change roles !")
            answer = getRoles()
            answer = "Coucou Timon, Maël, Léa et Alexis !\n\n C'est lundi, il est midi, c'est l'heure de changer les rôles !\n" + answer + "\n\nBonne semaine à tous !"
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, answer)
            time.sleep(60)

        # Each monday evening, send a message to say to not forget to take out the paper or the carton
        is_monday_evening = datetime.datetime.now().isocalendar()[2] == 1 and datetime.datetime.now().hour == 18 and datetime.datetime.now().minute == 0
        if is_monday_evening:
            papierOrCarton = getCartonOrPapier()
            answer = "Coucou tout le monde !\n\nC'est lundi soir, n'oubliez pas de sortir le {} pour qu'il soit rammassé demain matin !".format(papierOrCarton)
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, answer)
            time.sleep(60)

        # For each day of the Avent, send a message to the group to say who is the gifter and who is the receiver
        is_advent = datetime.datetime.now().month == 12
        is_advent_day = datetime.datetime.now().day <= 24
        is_advent_day_morning = is_advent and is_advent_day and datetime.datetime.now().hour == 7 and datetime.datetime.now().minute == 30
        if is_advent_day_morning:
            print("It's advent day morning, time to send a message to the group !")
            answer = get_avent_calendar_msg()
            bot.sendMessage(DRAHMSTRASSE_GROUP_ID, answer)
            time.sleep(60)
            
        time.sleep(10)

    except Exception as e:
        time.sleep(60)
        print("Exception occured: " + str(e))
        answer = "Je ne comprends pas ce message :("
        answer = answer + "\n\n" + "Exception: " + str(e)
        bot.sendMessage(ALEXIS_ID, answer)	
        time.sleep(60)
