import yaml

'''
This file contains some helpers function for the bot.
'''

def get_token():
    with open("bot_token.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile, yaml.FullLoader)
        token = cfg['telegram_bot_token']
    return token
    
def get_group_id():
    with open("bot_token.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile, yaml.FullLoader)
        group_id = cfg['bot_chat_id']
    
    return group_id

def get_colocs_id():
    with open("bot_token.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile, yaml.FullLoader)
        alexis_id = cfg['alexis_id']
        lea_id = ['lea_id']
        mael_id = ['mael_id']
        timon_id = ['timon_id']

    return [alexis_id,lea_id,mael_id,timon_id]