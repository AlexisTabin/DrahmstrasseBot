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

def setup_and_run_bot():

	'''
	Initialization du bot
	'''

	bot = telebot.TeleBot(utils.get_token(), parse_mode=None) # You can set parse_mode by default. HTML or MARKDOWN

	chat_id = utils.get_group_id()
	#chat_id = utils.get_colocs_id()[2] #2 pour Maeul, 0 pour Alexiiiis
	
	#Welcome message if you want:
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

	'Scheduled'

	#Wola jsp comment check lundi chaque 2 semaines avec CronTrigger
	# ... donc un peu du CACA, on check chaque lundi into on check si la semaine est paire ou impaire dans la function menage.changeroles()

	def update_roles(colocataires):
		answer = menage.changeRoles(colocataires=colocataires)
		bot.send_message(chat_id,answer)

	trigger_roles = CronTrigger(
			year="*", month="*", day="1", hour="10", minute="0", second="0"
		)

	scheduler.add_job(
		update_roles,
		trigger=trigger_roles,
		args=[colocataires],
		name="change_roles",
	)


	## On peut utiliser le même trigger pour le papier est carton
	def update_carton():
		answer = menage.getCartonOrPapier()
		bot.send_message(chat_id,answer)

	scheduler.add_job(
		update_carton,
		trigger=trigger_roles,
		name="change_carton",
	)





	'''
	Section social
	'''

	current_id_toxicity_poll = None

	@bot.message_handler(commands=['whoishere'])
	def whosthere(message):
		question = social.is_present_dinner()
		current_poll = bot.send_poll(chat_id, question, ['Oui','Oui INTO je ramène un.e +1','Oui INTO je cuisine','Oui, je cuisine ET je ramène un.e +1','C''est ciao'], is_anonymous=False)


	'Scheduled'



	'''
	Section chenil
	'''
	#@bot.message_handler(func=lambda message: True) #example for an arbitrary command
	#def echo_all(message):
	# bot.reply_to(message, message.text)
		
	@bot.message_handler(regexp='Ouais le bot ouais?') #example for an arbitrary command
	def test_maeul(message):
		bot.reply_to(message, "WOLA MAEUL TU TESTES UN TRUC AVEC MOI LE BOT TELEGRAM LE FUN LETSGOOOOOOOO")

	def test():
		answer = "Pardon je test un système de scheduler wola le spam"
		bot.send_message(chat_id,answer)

	trigger_test = CronTrigger(
			year="*", month="*", day="*", hour="*", minute="1", second="1-30"
		)

	#Test scheduler
	#scheduler.add_job(
	#	test,
		#trigger=trigger_test,
		#name="test",
	#)

	'''
	Section feu le bot FEUUUUUUUUUUUUUU
	'''
	bot.infinity_polling()

if __name__ == "__main__" :
	setup_and_run_bot()


