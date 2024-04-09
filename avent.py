import csv
import datetime
import time
from random import randrange

import requests
import yaml
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch

import telepot
from telepot.loop import MessageLoop


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

    answer = "En cette belle journée du {} Décembre, c'est au tour de {} d'offrir un cadeau à {} !".format(
        day, gifter, receiver)
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

        gifts_given[(gifter, receiver)] = gifts_given.get(
            (gifter, receiver), 0) + 1

    # Display the results
    for (gifter, receiver), count in gifts_given.items():
        offer = f"{count} cadeaux à {receiver}"
        if msg_from in gifter:
            answer = answer + "\n" + offer

    return answer


def getCadeauxPlannning(msg):
    msg_from = msg['from']['first_name']
    answer = "{}, voici quand et à qui tu dois offrir les cadeaux :\n".format(
        msg_from)

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
        if msg_from in day['gifter']:
            receiver = day['receiver']
            date = day['day']
            answer += "\nLe " + \
                (date if int(date) != 1 else '1er') + \
                " décembre pour " + receiver + "."

    answer += "\n\nBonne chance !"
    return answer
