import requests
import googlesearch
import mysql.connector
import pycountry

import json
import time
import os

from pathlib import Path
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase
from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase



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
        pass

    return utterance



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
# FORM ACTIONS                                                                                     #
####################################################################################################



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

        return [SlotSet('language', current_language)]



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
            results = db.simple_query('test_table', 'Quota, Consumption, Speed', f"Name = '{username}'")
            db.disconnect()
        except Exception as e:
            print(f'\n> ActionFetchQuota: [ERROR1] {e}')
            dispatcher.utter_message('Sorry, I couldn\'t connect to the database.')
            return [SlotSet('password', None)]

        if len(results) != 1:
            dispatcher.utter_message(f'Sorry, {username} is not a registered user.')
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
            
        elif intent == 'deny' and query != None:
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