import json
import telebot
import utils
import menage
import social

# Constants
LEA = 'Lea'
MARGAUX = 'Margaux'
TIMON = 'timon'
MAEL = 'Maël'
ALEXIS = 'Alexis'

colocataires = [MARGAUX, MAEL, LEA, ALEXIS]

# Initialize bot
bot = telebot.TeleBot(utils.get_token(), parse_mode=None)  # HTML or MARKDOWN optional
chat_id = utils.get_group_id()  # or utils.get_colocs_id()[2] if needed

# Send a welcome message when the bot is deployed (optional)
bot.send_message(chat_id, "Adieu l'ekip, je suis le Drahmbot et suis en ligne. Profitez-en :)")

# -----------------------------
# Define message handlers
# -----------------------------

@bot.message_handler(commands=['roles'])
def send_roles(message):
    answer = menage.getRoles(colocataires=colocataires)
    bot.send_message(message.chat.id, answer)

@bot.message_handler(commands=['papier'])
def send_papier_ou_carton(message):
    answer = menage.getCartonOrPapier()
    bot.send_message(message.chat.id, answer)

@bot.message_handler(commands=['lessive'])
def send_lessive(message):
    answer = menage.getCarteDeLessive()
    bot.send_message(message.chat.id, answer)

@bot.message_handler(commands=['whoishere'])
def whosthere(message):
    question = social.is_present_dinner()
    bot.send_poll(message.chat.id, question, ['Oui', 'Oui INTO je ramène un.e +1', 
                                              'Oui INTO je cuisine', 
                                              'Oui, je cuisine ET je ramène un.e +1', 
                                              'C\'est ciao'], is_anonymous=False)

@bot.message_handler(regexp='jeremie?')
def jeremied(message):
    bot.reply_to(message, "JEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEREMIE!")

# -----------------------------
# Lambda handler
# -----------------------------

def lambda_handler(event, context):
    """
    AWS Lambda entrypoint for Telegram webhook
    """
    if "body" in event:
        try:
            update = telebot.types.Update.de_json(event["body"])
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Error processing update: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps("ok")
    }

# -----------------------------
# Note on scheduled tasks
# -----------------------------
# APScheduler will NOT work reliably in Lambda.
# Use AWS EventBridge to trigger scheduled Lambda invocations.
# Example: an EventBridge rule triggering this Lambda every Monday at 10:00.
# You can pass a special payload in the event to run scheduled jobs.

