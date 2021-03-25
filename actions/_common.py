import requests
import googlesearch
import mysql.connector
import pycountry

import json
import random
import time
import os

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Text, Optional

from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import ActionExecuted, ActionReverted, ActiveLoop, AllSlotsReset, SlotSet, FollowupAction, ReminderCancelled, ReminderScheduled, SessionStarted, UserUtteranceReverted
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase
from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase
from rasa_sdk.types import DomainDict



####################################################################################################

conversation_data = {} # {sender_id: {'password_tries': 0}, ...}

lang_list = ['English', 'French', 'Arabic', 'Armenian'] # Same as slot values

text_does_it_work = [
    'Does it work now?',
    'Est-ce que ça marche maintenant?',
    'هل يعمل الآن؟',
    'Հիմա աշխատու՞մ է?']

text_anything_else = [
    'Anything else I can help with?',
    'Est-ce que je peux vous aider avec autre chose?',
    'أي شيء آخر يمكنني المساعدة به؟',
    'Ուրիշ ինչ-որ բան կարող եմ օգնել:']

buttons_yes_no_emoji = [
    {'title': '👍', 'payload': '/affirm'},
    {'title': '👎', 'payload': '/deny'}]

button_stop_emoji = [{'title': '🚫', 'payload': '/stop'}]

buttons_yes_no_stop_emoji = buttons_yes_no_emoji + button_stop_emoji



class DatabaseConnection:
    connection = None
    cursor = None
    query = None

    def __init__(self):
        if self.connection is None:
            self.connect()

    def connect(self):
        self.connection = mysql.connector.connect(
            host     = 'localhost', #'194.126.17.114',
            database = 'esib_fyp_database',#'rasa_db',
            user     = 'rasa',#'rasaq', # granted all privileges on rasa_db.* to rasaq@%
            password = 'rasa')#'rasa')

    def disconnect(self):
        self.cursor.close()
        self.connection.close()

    
    def query(self, sql):
        result = []

        print(f'\n> DatabaseConnection: {sql}')

        self.cursor = self.connection.cursor()
        self.cursor.execute(sql)

        for row in self.cursor:
            result.append(row)
            print(row)

        return result

    '''
    table:    Argument of FROM   - String
    columns:  Argument of SELECT - String
    condtion: Argument of WHERE  - String
    '''
    def simple_query(self, table, columns = '*', condition = None):
        result = []

        sql = f"SELECT {columns} FROM {table}"

        if condition:
            sql += f" WHERE {condition}"

        return self.query(sql)

    def count(self, table, condition = None):
        return len(self.simple_query(table, '*', condition))



def announce(action, tracker = None):
    output = '>>> Action: ' + action.name()
    output = '=' * min(100, len(output)) + '\n' + output
    if tracker:
        try:
            msg = tracker.latest_message
            slots = tracker.slots
            filled_slots = {}
            output += '\n- Text:       ' + str(msg['text'])
            output += '\n- Intent:     ' + str(msg['intent']['name'])
            output += '\n- Confidence: ' + str(msg['intent']['confidence'])
            output += '\n- Entities:   ' + ', '.join(msg['entities'])
            output += '\n- Slots:      '
            for slot_key, slot_value in slots.items():
                if slot_value is not None:
                    filled_slots[slot_key] = slot_value
            if len(filled_slots) > 0:
                for slot_key, slot_value in filled_slots.items():
                    output += str(slot_key) + ': ' + str(slot_value) + ', '
                output = output[:-2]
        except Exception as e:
            print(f'\n> announce: [ERROR] {e}')
    print(output)



def reset_slots(tracker, slots, exceptions = []):
    events = []
    none_slots = []

    for exception in exceptions:
        if exception in slots:
            slots.remove(exception)

    for slot in slots:
        if tracker.get_slot(slot) is not None:
            none_slots.append(slot)
    
    for slot in none_slots:
        events.append(SlotSet(slot, None))

    print('\n> reset_slots:', ', '.join(none_slots))

    return events



def get_lang(tracker):
    try:
        lang = tracker.slots['language'].title()
        return lang
    except Exception as e:
        return 'English'



def get_lang_index(tracker):
    return lang_list.index(get_lang(tracker))



''' utter_list is a list of outputs in multiple lanaguages, each output can be a string or a list of strings '''
def get_text_from_lang(tracker, utter_list = []):
    lang_index = get_lang_index(tracker)

    if not utter_list: # No text was given for any language
        return '[NO TEXT DEFINED]'

    if lang_index >= len(utter_list): # No text defined for current language
        lang_index = 0

    text = utter_list[lang_index]

    if isinstance(text, list): # If a list is given for the language, choose a random item
        text = str(text[random.randint(0,len(text)-1)])
    else:
        text = str(text)
    
    return text 



def get_response_from_lang(tracker, response):
    return response + '_' + get_lang(tracker)



def get_buttons_from_lang(tracker, titles = [], payloads = []):
    lang_index = get_lang_index(tracker)
    buttons    = []

    if lang_index >= len(payloads): # No text defined for current language
        lang_index = 0
    
    for i in range(min(len(titles[lang_index]), len(payloads))):
        buttons.append({'title': titles[lang_index][i], 'payload': payloads[i]})

    return buttons



async def global_validate_username(value, dispatcher, tracker, domain):
    if not tracker.get_slot('loggedin'):
        username   = value.title()
        login_type = 'Username'
        count      = 0
        
        db = DatabaseConnection()

        count = db.count('user_info', f"Username = '{username}'")
        if count == 1:
            login_type = 'Username'
        else:
            count = db.count('user_info', f"L_Number = '{username}'")
            if count == 1:
                login_type = 'L_Number'
            else:
                count = db.count('user_info', f"Phone_Number = '{username}'")
                if count == 1:
                    login_type = 'Phone_Number'
                else:
                    count = 0

        db.disconnect()

        if count == 1:
            print('\n> validate_username:', login_type, username)
            return {'username': username.title(), 'loggedin': False, 'login_type': login_type}

        elif count == 0:
            text = get_text_from_lang(
                tracker,
                ['Sorry, {} is not recognized.'.format(username),
                'Désolé, {} n\'est pas enregistré.'.format(username),
                'عذرًا ، {} ليس اسم مستخدم مسجلاً ، رقم L ، لرقم هاتف. يرجى المحاولة مرة أخرى أو الضغط على "🚫" للتوقف.'.format(username),
                'Ներողություն, {} գրանցված Մականուն, L համար, հեռախոսահամար չէ:'.format(username)])
            print('\nBOT:', text)
            dispatcher.utter_message(text)
            return {'username': None, 'loggedin': False, 'login_type': None}

        else:
            login_type = login_type.replace('_', ' ')
            text = f'There seems to be {count} users with the {login_type} {username}. Please report this error.'
            print('\nBOT:', text)
            dispatcher.utter_message(text)
            return {'username': None, 'loggedin': False, 'login_type': None}
    
    else: # Already logged in
        text = get_text_from_lang(
            tracker,
            ['You are already logged in. If you want to log out, please say "log out".',
            'Vous êtes déjà connecté. Si vous souhaitez vous déconnecter, veuillez dire «déconnexion» ou «log out».',
            'لقد قمت بتسجيل الدخول بالفعل. إذا كنت تريد الخروج ، من فضلك قل "تسجيل الخروج" أو "log out".',
            'Դուք արդեն մուտք եք գործել համակարգ: Եթե ցանկանում եք դուրս գալ, խնդրում ենք ասել «դուրս գալ» կամ «log out»:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text)
        return {'password': 'secret', 'loggedin': True}



async def global_validate_password(value, dispatcher, tracker, domain):
    if not tracker.get_slot('loggedin'):
        username = tracker.get_slot('username')
        password = value
        login_type = tracker.get_slot('login_type')

        db = DatabaseConnection()
        count = db.count('user_info', f"{login_type} = '{username}' AND Password = '{password}'")
        db.disconnect()

        if count == 1:
            print('\n> validate_password: Login with', username)
            return {'password': 'secret', 'loggedin': True}

        else:
            text = get_text_from_lang(
                tracker,
                ['Sorry, you entered an incorrect password for {}.'.format(username),
                'Désolé, vous avez entré un mot de passe incorrect pour {}.'.format(username),
                'عذرًا ، لقد أدخلت كلمة مرور غير صحيحة لـ {}'.format(username),
                'Ներողություն, դուք սխալ գաղտնաբառ եք մուտքագրել {} - ի համար:'.format(username)])
            print('\nBOT:', text)
            dispatcher.utter_message(text)
            return {'password': None, 'loggedin': False}

    else: # Already logged in
        username = tracker.get_slot('username').title()
        text = get_text_from_lang(
            tracker,
            ['You are logged in as {}.'.format(username),
            'Vous êtes connecté en tant que {}'.format(username),
            'أنت مسجل دخولك باسم {}.'.format(username),
            'Դուք մուտք եք գործել որպես {}:'.format(username)])
        print('\nBOT:', text)
        dispatcher.utter_message(text)
        return {'username': username, 'password': 'secret', 'loggedin': True}
