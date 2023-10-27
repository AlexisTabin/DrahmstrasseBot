import time
import random
import datetime
import telepot
import yaml
from telepot.loop import MessageLoop
import pandas as pd
import requests
from bs4 import BeautifulSoup
from random import randrange


LEA = 'LEA'
TIMON = 'TIMON'
MAEL = 'MAEUL'
ALEXIS = 'ALEXIS'

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

    if artist == "Ninho":
        quote = quotes[randrange(len(quotes))]
        return quote.text + "\n- " + artist + "\n" + "https://www.youtube.com/watch?v=3BI1K6oXTqQ"
    if artist == "Niska":
        quote = quotes[randrange(len(quotes))]
        return quote.text + "\n- " + artist + "\n" + "https://www.youtube.com/watch?v=GaYNpipK8hg"
    
    links = artist_soup.find_all("a", attrs={'class':'wixui-rich-text__text'})
    links = [l for l in links if "youtube" in l['href']]
    index = 0 if (len(links) != len(quotes)) else randrange(len(quotes))
    quote = quotes[index]
    link = links[index]
   
    return quote.text + "\n- " + artist + "\n" + link['href']

def get_avent_calendar_msg():
    answer = "C'est l'Avent !"
    # read avent_calendar.csv
    calendar = pd.read_csv('avent_calendar.csv')
    # get current day
    day = datetime.datetime.now().day

    day = 1
    # day must be between 1 and 24
    if day < 1 or day > 24:
        return "Ce n'est plus l'Avent ! :("
    

    # get current day's gifter and receiver from the csv file
    gifter = calendar['gifter'][day - 1]
    receiver = calendar['receiver'][day - 1]

    if day == 1:
        day = "1er"
    answer = "En cette belle journée du {} Décembre, c'est au tour de {} d'offrir un cadeau à {} !".format(day, gifter, receiver)
    return answer

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
            answer = "C'est la semaine du Papier !"
        else:
            answer = "C'est la semaine du Carton !"
        bot.sendMessage(chat_id, answer)

    elif command == '/time':
        msg = get_avent_calendar_msg()
        bot.sendMessage(chat_id, msg)

    elif command == '/avent':
        # if we are still not in december, print the number of days left
        if datetime.datetime.now().month != 12:
            answer = "Il reste {} jours avant le début de l'Avent !".format((datetime.datetime(2023, 12, 1) - datetime.datetime.now()).days)
        else:
            answer = get_avent_calendar_msg()
        bot.sendMessage(chat_id, answer)

    elif command == '/rendu':
        # print number of days left before the 15th of december
        answer = "Timon, il te reste {} jours avant ton rendu !".format((datetime.datetime(2023, 12, 15) - datetime.datetime.now()).days)
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

# read token from yml file
with open("bot_token.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, yaml.FullLoader)
    # get token from yml file 
    token = cfg['telegram_bot_token']

bot = telepot.Bot(token)

MessageLoop(bot, handle).run_as_thread()
print('I am listening ...')

while 1:
    time.sleep(10)
