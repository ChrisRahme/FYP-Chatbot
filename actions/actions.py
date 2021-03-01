import requests
import googlesearch
import mysql.connector
import pycountry

import json
import time
import os

from pathlib import Path
from typing import Any, Dict, List, Text, Optional

from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase
from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase
from rasa_sdk.types import DomainDict



####################################################################################################
# HELPER CLASSES & FUNCTIONS                                                                       #
####################################################################################################



class DatabaseConnection:
    connection = None
    cursor = None
    query = None

    def __init__(self):
        if self.connection == None:
            self.connect()

    def connect(self):
        self.connection = mysql.connector.connect(
            host='194.126.17.114',
            database='rasa_db',
            user='rasaq', # granted all privileges on rasa_db.* to rasaq@%
            password='rasa'
        )

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



def get_utter_from_lang(tracker, utter_en, utter_fr, utter_ar, utter_hy):
    current_language = 'English'
    utterance = utter_en

    try:
        current_language = tracker.slots['language'].title()
        if current_language == 'French':
            utterance = utter_fr
        elif current_language == 'Arabic':
            utterance = utter_ar
        elif current_language == 'Armenian':
            utterance = utter_hy
    except Exception as e:
        print(f'\n> get_utter_from_lang: [ERROR] {e}')

    return utterance



def get_template_from_lang(tracker, template):
    current_language = 'English'

    try:
        current_language = tracker.slots['language'].title()
        if current_language == 'French':
            template = template + '_fr'
        elif current_language == 'Arabic':
            template = template + '_ar'
        elif current_language == 'Armenian':
            template = template + '_hy'
        else:
            template = template + '_en'
    except Exception as e:
        print(f'\n> get_template_from_lang: [ERROR] {e}')

    return template



####################################################################################################
# SLOTS                                                                                            #
####################################################################################################



class ActionAskUsername(Action):
    def name(self):
        return 'action_ask_username'

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        utterance = get_utter_from_lang(
            tracker,
            'Please enter your username.',
            'S\'il vous plaît entrez votre nom d\'utilisateur.',
            '.(username) الرجاء إدخال اسم المستخدم',
            'Խնդրում ենք մուտքագրել ձեր օգտվողի անունը: (username).'
        )            
        dispatcher.utter_message(utterance)
        return []



class ActionAskPassword(Action):
    def name(self):
        return 'action_ask_password'

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        utterance = get_utter_from_lang(
            tracker,
            'Please enter your password.',
            'S\'il vous plaît entrez votre mot de passe.',
            '.(password) من فضلك أدخل رقمك السري',
            'Խնդրում ենք մուտքագրել ձեր գաղտնաբառը (username).'
        )            
        dispatcher.utter_message(utterance)
        return []



####################################################################################################
# FORM VALIDATION ACTIONS                                                                          #
####################################################################################################



class ValidateFormQueryQuota(FormValidationAction):
    def name(self):
        return 'validate_form_query_quota'

    
    # Custom Slot Mappings: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        required_slots = [predefined_slots[1], predefined_slots[0]] # To ask for username before password
        return required_slots


    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_username(self, value, dispatcher, tracker, domain):
        username = value.lower()

        db = DatabaseConnection()
        count = db.count('user_info', f"Username = '{username}'")
        db.disconnect()

        if count == 1:
            return {'username': username}

        elif count == 0:
            utterance = get_utter_from_lang(
                tracker,
                'Sorry, {} is not a registered user.'.format(username),
                'Désolé, {} n\'est pas un utilisateur enregistré.'.format(username),
                'عذرًا، {} ليس مستخدمًا مسجلاً'.format(username),
                'Ներողություն, {} - ը գրանցված օգտվող չէ:'.format(username)
            )
            dispatcher.utter_message(utterance)
            return {'username': None}

        else:
            dispatcher.utter_message(f'There seems to be {count} users with the username {username}. Please report this error.')
            return {'username': None}
    

    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_password(self, value, dispatcher, tracker, domain):
        username = tracker.get_slot('username')
        password = tracker.get_slot('password')

        db = DatabaseConnection()
        count = db.count('user_info', f"Username = '{username}' AND Password = '{password}'")
        db.disconnect()

        if count == 1:
            return {'password': password}

        else:
            utterance = get_utter_from_lang(
                tracker,
                'Sorry, you entered an incorrect password for {}.'.format(username),
                'Désolé, vous avez entré un mot de passe incorrect pour {}.'.format(username),
                'عذرًا ، لقد أدخلت كلمة مرور غير صحيحة لـ {}'.format(username),
                'Ներողություն, դուք սխալ գաղտնաբառ եք մուտքագրել {} - ի համար:'.format(username)
            )
            dispatcher.utter_message(utterance)
            return {'password': None}



####################################################################################################
# FORM ACTIONS                                                                                     #
####################################################################################################



####################################################################################################
# TEMPLATE UTTERANCES                                                                              #
####################################################################################################



class ActionUtterGreet(Action):
    def name(self):
        return 'action_greet'
    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(template = get_template_from_lang(tracker, 'utter_greet'))
        return []



class ActionUtterGoodbye(Action):
    def name(self):
        return 'action_goodbye'
    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(template = get_template_from_lang(tracker, 'utter_goodbye'))
        return []
            


####################################################################################################
# TEXT UTTERANCES                                                                                  #
####################################################################################################


class ActionRecoverCredentials(Action):
    def name(self):
        return 'action_recover_credentials'


    def run(self, dispatcher, tracker, domain):
        url = 'https://myaccount.idm.net.lb/_layouts/15/IDMPortal/ManageUsers/ResetPassword.aspx'
        url = '\n\n' + url

        utterance = get_utter_from_lang(
            tracker,
            'If you need help recovering your IDM ID or your password, click on the link below:',
            'Si vous avez besoin d\'aide pour récupérer votre ID IDM ou votre mot de passe, cliquez sur le lien ci-dessous:',
            'لا مشكلة. إذا كنت بحاجة إلى مساعدة في استعادة معرّف IDM أو كلمة مرورك ، فانقر على الرابط أدناه:',
            'Ոչ մի խնդիր. Եթե ձեր IDM ID- ն կամ գաղտնաբառն վերականգնելու համար օգնության կարիք ունեք, կտտացրեք ստորև նշված հղմանը.'
        )            
        
        dispatcher.utter_message(text = utterance + url)

        return []



####################################################################################################
# ACTIONS                                                                                          #
####################################################################################################



class ActionChangeLanguage(Action):
    def name(self):
        return 'action_change_language'
    

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        print(str(tracker.latest_message))

        buttons = [ # https://forum.rasa.com/t/slots-set-by-clicking-buttons/27629
            {'title': 'English',  'payload': '/set_language{"language": "English"}'},
            {'title': 'Français', 'payload': '/set_language{"language": "French"}'},
            {'title': 'عربي',     'payload': '/set_language{"language": "Arabic"}'},
            {'title': 'հայերեն',  'payload': '/set_language{"language": "Armenian"}'}
        ]
        
        utterance = get_utter_from_lang(
            tracker,
            'Choose a language:',
            'Choisissez une langue:',
            ':اختر لغة',
            'Ընտրեք լեզու ՝'
        )            
        
        dispatcher.utter_message(text = utterance, buttons = buttons)

        return []



class ActionSetLanguage(Action):
    def name(self) -> Text:
        return 'action_set_language'
    

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        print(str(tracker.latest_message))

        current_language = tracker.slots['language'].title()
        
        if current_language == 'English':
            utterance = 'The language is now English.'
        elif current_language == 'French':
            utterance = 'La langue est maintenant le Français.'
        elif current_language == 'Arabic':
            utterance = 'اللغة الآن هي العربية.'
        elif current_language == 'Armenian':
            utterance = 'Լեզուն այժմ հայերենն է:'
        else: 
            current_language == 'English'
            utterance = 'I only understand English, French, Arabic, and Armenian. The language is now English.'
        
        dispatcher.utter_message(utterance)

        return [] #[SlotSet('language', current_language)]



class ActionFetchQuota(Action):
    def name(self) -> Text:
        return 'action_fetch_quota'
    

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        print(str(tracker.latest_message))

        results = None
        username = tracker.get_slot('username')
        password = tracker.get_slot('password')

        try:
            db = DatabaseConnection()
            #results = db.simple_query('test_table', 'Quota, Consumption, Speed', f"Name = '{username}'")
            results = db.query("SELECT Quota, Consumption, Speed "
                "FROM `user_info` INNER JOIN `consumption` "
                "ON `user_info`.`ID` = `consumption`.`UserID` "
                f"WHERE Username = '{username}' AND Password = '{password}'")
            db.disconnect()
        except Exception as e:
            print(f'\n> ActionFetchQuota: [ERROR1] {e}')
            dispatcher.utter_message('Sorry, I couldn\'t connect to the database.')
            return [SlotSet('password', None)]

        if len(results) != 1:
            dispatcher.utter_message(f'Sorry, {username} is not a registered user or your password is incorrect.')
            return [SlotSet('username', None), SlotSet('password', None)]

        try:
            quota, consumption, speed = results[0]
            if int(quota) == -1:
                utterance = get_utter_from_lang(
                    tracker,
                    'You spent {} GB of your unlimited quota this month.'.format(consumption),
                    'Vous avez dépensé {} Go de votre quota illimité pour ce mois.'.format(consumption),
                    '.لقد أنفقت {} غيغابايت من حصتك غير المحدودة هذا الشهر'.format(consumption),
                    'Դուք անցկացրել {} ԳԲ ձեր անսահման քվոտայի այս ամսվա.'.format(consumption)
                )
                dispatcher.utter_message(utterance)
            else:
                ratio = consumption*100/quota
                utterance = get_utter_from_lang(
                    tracker,
                    'You spent {} GB ({}%) of your {} GB quota for this month.'.format(consumption, ratio, quota),
                    'Vous avez dépensé {} Go ({}%) de votre quota de {} Go pour ce mois.'.format(consumption, ratio, quota),
                    '.لقد أنفقت {} غيغابايت ({}٪) من حصتك البالغة {} غيغابايت لهذا الشهر'.format(consumption, ratio, quota),
                    'Այս ամսվա համար ծախսեցիք ձեր {} ԳԲ քվոտայի {} ԳԲ ({}%).'.format(consumption, ratio, quota)
                )
                dispatcher.utter_message(utterance)
        except Exception as e:
            print(f'\n> ActionFetchQuota: [ERROR2] {e}')
            dispatcher.utter_message('Sorry, there was an error.')

        return [SlotSet('password', None)]



class ActionCheckExistence(Action):
    knowledge = Path('data/lookups/pokemon_name.txt').read_text().split('\n')

    def name(self) -> Text:
        return 'action_check_existence'

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        print(str(tracker.latest_message))

        pokemon_name = None
        latest = tracker.latest_message
        
        for blob in latest['entities']:
            if blob['entity'] == 'pokemon_name':
                name = blob['value'].title()
                if name.lower() in self.knowledge:
                    dispatcher.utter_message(text=f'Yes, {name} is a Pokémon.')
                    pokemon_name = name
                else:
                    dispatcher.utter_message(text=f'{name} is not a Pokémon.')
        
        if pokemon_name:
            return [SlotSet('pokemon_name', pokemon_name)]
        
        return []



class ActionCheckWeather(Action):
    def name(self):
        return 'action_check_weather'

    def alpha2_to_name(self, alpha2):
        try:
            name = pycountry.countries.get(alpha_2=alpha2).name
            return name
        except:
            return alpha2

    def call_api(self, city_name):
        api_key = 'd24a63d18af95420958d7bb8b5839016'
        url = f'http://api.openweathermap.org/data/2.5/weather?appid={api_key}&q={city_name}'
        
        try:
            response = requests.get(url).json() 
            result = {'response': True, 'code': str(response['cod'])}

            if result['code'] == '200':
                result['temperature'] = str(round(response['main']['temp'] - 273.15, 1))
                result['city']        = city_name.title()
                result['country']     = ', {}'.format(self.alpha2_to_name(response['sys']['country'])) if (('sys' in response) and ('country' in response['sys'])) else ''

            return result

        except:
            return {'response': False}        


    def utter_weather(self, city_name):
        result = self.call_api(city_name)

        if result['response']:
            if result['code'] == '200':
                return 'Temperature is currently {} °C in {}{}.'.format(result['temperature'], result['city'], result['country'])
            elif result['code'] == '404':
                return 'Sorry, I could not find a city or country named {}.'.format(city_name.title())
            else:
                return 'Sorry, there was an error looking for the weather in {} (Error {}).'.format(city_name.title(), result['code'])
        else:
            return f'Sorry, the weather server is not responding.'

    
    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        print(str(tracker.latest_message))

        latest = tracker.latest_message
        
        if latest['entities']:
            for blob in latest['entities']: # To get it as a slot: tracker.get_slot('city_name')
                if blob['entity'] == 'city_name':
                    city_name = blob['value']
                    result = self.utter_weather(city_name)
                    dispatcher.utter_message(result)
                return [SlotSet('city_name', city_name)]
        
        elif tracker.slots['city_name']:
            city_name  = tracker.slots['city_name']
            result = self.utter_weather(city_name)
            dispatcher.utter_message(result)
        
        else:
            dispatcher.utter_message('Please provide a city or country to check the weather.')
        
        return []



class ActionOutOfScope(Action):
    def name(self):
        return 'action_out_of_scope'

    def run(self, dispatcher, tracker, domain):
        print('='*100 + '\n' + self.name())
        print(str(tracker.latest_message))

        latest = tracker.latest_message
        intent = latest['intent']['name']
        query  = tracker.slots['out_of_scope']

        if intent == 'out_of_scope':
            dispatcher.utter_message('Sorry, I don\'t understand. Do you want me to search that on Google?')
            return [SlotSet('out_of_scope', latest['text'])]

        elif intent == 'affirm' and query != None:
            try:
                urls = [url for url in googlesearch.search(
                    query=query,
                    tld='com.lb',
                    lang='en',
                    num=5,
                    stop=5,
                    pause=1,
                    extra_params={'filter': '0'})
                ]
                dispatcher.utter_message('Here are the top results:')

                for url in urls:
                    dispatcher.utter_message(str(url))

            except Exception as e:
                dispatcher.utter_message('Sorry, I could not comlete the search.\n' + str(e))
                print('[ERROR] ' + str(e))

            return [SlotSet('out_of_scope', None)]
            
        elif (intent == 'deny' or intent == 'stop') and query != None:
            dispatcher.utter_message('Okay.')
            return [SlotSet('out_of_scope', None)]



####################################################################################################
# END                                                                                              #
####################################################################################################
'''
tracker.latest_message: dict{
  intent: dict{id, name, confidence}
  entities: list[string]
  text: string
  message_id: string
  metadata: dict{}
  intent_ranking: list[intent]
  response_selector: dict{
    all_retrieval_intents: list[],
    default: dict{
      response: dict{id, response_templates, confidence, intent_response_key, template_name},
      ranking: list[]
    }
  }
}
'''