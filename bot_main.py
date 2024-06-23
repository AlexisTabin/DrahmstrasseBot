import telebot

import utils
import menage
import social

import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


LEA = 'Lea'
TIMON = 'timon'
MAEL = 'Maël'
ALEXIS = 'Alexis'

colocataires=[LEA, MAEL, TIMON, ALEXIS]

'''
Initialization du bot
'''

bot = telebot.TeleBot(utils.get_token(), parse_mode=None) # You can set parse_mode by default. HTML or MARKDOWN
chat_id = utils.get_group_id()

#bot.send_message(chat_id,'Bonjour, je suis le Drahmbot.')

'''
Initialization du scheduler
'''

scheduler = BackgroundScheduler()
scheduler.start()


'''
Section tâches de ménage
'''

'Requests'

@bot.message_handler(commands=['roles'])
def send_roles(message):
	answer = menage.getRoles(colocataires=colocataires)
	bot.send_message(chat_id,answer)

@bot.message_handler(commands=['papier'])
def send_papier_ou_carton(message):
	answer = menage.getCartonOrPapier()
	bot.send_message(chat_id,answer)

@bot.message_handler(commands=['lessive'])
def send_lessive(message):
	answer = menage.getCarteDeLessive()
	bot.send_message(chat_id,answer)


'''
Section social
'''
'Requests'

@bot.message_handler(commands=['whosthere'])
def toxicity_detected(message):
	question = social.is_toxic()
	current_poll = bot.send_poll(chat_id, question, ['Oui','Non'], is_anonymous=False)
	current_id_toxicity_poll =  current_poll.id

	print(current_id_toxicity_poll)
	#@bot.poll_handler()


@bot.poll_handler(func=lambda message: (message.id == current_id_toxicity_poll))
def handle_toxicity_poll(poll):
	print(poll.total_voter_count)
	if poll.total_voter_count >=4: ## Check si tout le monde a voted
			if poll.options[0].voter_count > poll.options[1].voter_count: ## Check si oui ou non win

				bot.send_message(chat_id,'Vous avez tranché, la toxicité est trop élevée... Je vais donc agir en conséquence.')


				all_ids =  utils.get_colocs_id()
				for user_id in all_ids:
					bot.restrict_chat_member(chat_id, user_id, until_date=time()+300) # Mute tout le monde 5 min



'''
Section chenil
'''

	
@bot.message_handler(regexp='Ouais le bot ouais?') #example for an arbitrary command
def test_maeul(message):
	bot.reply_to(message, "WOLA MAEUL TU TESTES UN TRUC AVEC MOI LE BOT TELEGRAM LE FUN LETSGOOOOOOOO")


'''
Section schedulers

How to handle schedulers? Genre on veut envoyer les nouveaux roles chaque 2 semaines, est-ce qu'on lance un nouveau thread qui fait un bot.send_message?
Et qui check la date et l'heure chaque 10 min ou comme ça?
Ou on fait avec le polling du bot directement?

Idée: utiliser APScheduler:
https://apscheduler.readthedocs.io/en/3.x/userguide.html

A discuter avec ALEXIIIIIIIIIIIIIIIIIIS
'''

#roles

#papier

#demander automatiquement si présent ce soir?

'''
Section feu le bot FEUUUUUUUUUUUUUU
'''

bot.infinity_polling()

