from random import randrange

import requests
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch


def getQuote():
    url = 'https://quotes.toscrape.com/'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')

    quotes = soup.find_all("div", attrs={'class': 'quote'})
    print(quotes)
    q = quotes[randrange(len(quotes))]
    q_text = q.find("span", attrs={'class': 'text'}).text
    print("q_text: " + str(q_text))
    print("--------------------"*10)
    print("Q again : " + str(q))
    q_author_tag = q.find("small", attrs={'class': 'author'})
    print("q_author_tag: " + str(q_author_tag))
    q_author = q_author_tag.text if q_author_tag else "Unknown Author"

    fmt_text = "{} ~ {}".format(q_text, q_author)

    return fmt_text


def getRap():
    url = 'https://www.lymu.net/punchlines-citations-rap'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    artists = soup.find_all(
        "span", attrs={'class': 'StylableButton2545352419__label wixui-button__label'})
    artists = [str(a.text).split(" ")[-1]
               for a in artists if a.text != "Connexion"]
    artist = artists[randrange(len(artists))]
    print("artist: " + str(artist))

    if artist == "Ninho":
        artist_url = "https://www.lymu.net/punchlines-ninho"

    else:
        artist_url = "https://www.lymu.net/{}-punchlines".format(
            str(artist).lower())

    artist_r = requests.get(artist_url, headers=HEADERS)
    artist_soup = BeautifulSoup(artist_r.text, 'html.parser')
    quotes = artist_soup.find_all(
        "span", attrs={'class': 'color_14 wixui-rich-text__text'})
    # if artist == "Ninho":
    #     quote = quotes[randrange(len(quotes))]
    #     return quote.text + "\n- " + artist + "\n" + "https://www.youtube.com/watch?v=3BI1K6oXTqQ"
    # if artist == "Niska":
    #     quote = quotes[randrange(len(quotes))]
    #     return quote.text + "\n- " + artist + "\n" + "https://www.youtube.com/watch?v=GaYNpipK8hg"

    if artist in ["Damso", "Ninho", "Niska"]:
        albums = artist_soup.find_all(
            "span", attrs={'class': 'color_15 wixui-rich-text__text'})
        albums = [str(a.text).split(' ')[-1]
                  for a in albums[2:] if '-' in a.text]
        links = [VideosSearch(artist + ' ' + album, limit=1)
                 for album in albums]
        links = [l.result()['result'][0]['link'] for l in links]
        index = randrange(min(len(links), len(quotes))) if (
            len(links) != len(quotes)) else randrange(len(quotes))
        quote = quotes[index]
        link = links[index]

        return quote.text + "\n- " + artist + "\n" + link
    else:
        links = artist_soup.find_all(
            "a", attrs={'class': 'wixui-rich-text__text'})
        links = [l for l in links if "youtube" in l['href']]
        index = randrange(min(len(links), len(quotes))) if (
            len(links) != len(quotes)) else randrange(len(quotes))
        quote = quotes[index]
        link = links[index]

        return quote.text + "\n- " + artist + "\n" + link['href']
