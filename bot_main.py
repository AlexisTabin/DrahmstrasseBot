import telebot

import utils
import menage



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
Section tâche de ménages
'''
@bot.message_handler(commands=['roles'])
def send_roles(message):
	answer = menage.getRoles(colocataires=colocataires)
	bot.send_message(chat_id,answer)

@bot.message_handler(commands=['papier'])
def send_paper_ou_carton(message):
	answer = menage.getCartonOrPapier()
	bot.send_message(chat_id,answer)

'''
Section chenil
'''
#@bot.message_handler(func=lambda message: True) #example for an arbitrary command
#def echo_all(message):
# bot.reply_to(message, message.text)
	
@bot.message_handler(regexp='Ouais le bot ouais?') #example for an arbitrary command
def test_maeul(message):
	bot.reply_to(message, "WOLA MAEUL TU TESTES UN TRUC AVEC MOI LE BOT TELEGRAM LE FUN LETSGOOOOOOOO")


'''
Section feu le bot FEUUUUUUUUUUUUUU
'''
bot.infinity_polling()