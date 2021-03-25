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

from . import _common

####################################################################################################




class ActionUtterGoodbye(Action):
    def name(self):
        return 'action_utter_goodbye'
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        dispatcher.utter_message(template = _common.get_response_from_lang(tracker, 'utter_goodbye'))
        return []
            


class ActionUtterYoureWelcome(Action):
    def name(self):
        return 'action_utter_youre_welcome'
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        response = _common.get_response_from_lang(tracker, 'utter_youre_welcome')
        print('\nBOT:', response)
        dispatcher.utter_message(template = response)
        return []



####################################################################################################
# API ACTIONS                                                                                      #
####################################################################################################



class ActionFetchQuota(Action):
    def name(self) -> Text:
        return 'action_fetch_quota'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)

        if tracker.get_slot('loggedin') or tracker.get_slot('password') == 'secret':
            results    = None
            username   = tracker.get_slot('username')
            login_type = tracker.get_slot('login_type')

            try:
                db = _common.DatabaseConnection()
                results = db.query("SELECT Quota, Consumption, Speed "
                    "FROM `user_info` INNER JOIN `consumption` "
                    "ON `user_info`.`ID` = `consumption`.`UserID` "
                    f"WHERE {login_type} = '{username}'")
                db.disconnect()
            except Exception as e:
                print(f'\n> ActionFetchQuota: [ERROR] {e}')
                dispatcher.utter_message('Sorry, I couldn\'t connect to the database.')
                return [SlotSet('username', None), SlotSet('password', None), SlotSet('loggedin', False)]

            if len(results) != 1:
                utterance = f'Sorry, {username} is not a registered username.'
                print('\nBOT:', utterance)
                dispatcher.utter_message(utterance)
                return [SlotSet('username', None), SlotSet('password', None), SlotSet('loggedin', False)]

            try:
                quota, consumption, speed = results[0]
                if int(quota) == -1:
                    utterance = _common.get_text_from_lang(
                        tracker,
                        ['You spent {} GB of your unlimited quota this month.'.format(consumption),
                        'Vous avez dépensé {} Go de votre quota illimité pour ce mois.'.format(consumption),
                        '.لقد أنفقت {} غيغابايت من حصتك غير المحدودة هذا الشهر'.format(consumption),
                        'Դուք անցկացրել {} ԳԲ ձեր անսահման քվոտայի այս ամսվա.'.format(consumption)])
                    print('\nBOT:', utterance)
                    dispatcher.utter_message(utterance)
                else:
                    ratio = consumption*100/quota
                    utterance = _common.get_text_from_lang(
                        tracker,
                        ['You spent {} GB ({}%) of your {} GB quota for this month.'.format(consumption, ratio, quota),
                        'Vous avez dépensé {} Go ({}%) de votre quota de {} Go pour ce mois.'.format(consumption, ratio, quota),
                        '.لقد أنفقت {} غيغابايت ({}٪) من حصتك البالغة {} غيغابايت لهذا الشهر'.format(consumption, ratio, quota),
                        'Այս ամսվա համար ծախսեցիք ձեր {} ԳԲ քվոտայի {} ԳԲ ({}%).'.format(consumption, ratio, quota)])
                    print('\nBOT:', utterance)
                    dispatcher.utter_message(utterance)
            except Exception as e:
                print(f'\n> ActionFetchQuota: [ERROR] {e}')
                dispatcher.utter_message('Sorry, there was an error.')
        
        else: # Not logged in
            utterance = _common.get_text_from_lang(
                tracker,
                ['You are not logged in. Please type "log in" to log in.',
                'Vous n\'êtes pas connecté. Veuillez ecrire «connexion» ou «log in» pour vous connecter.',
                'أنت لم تسجل الدخول. من فضلك قل "تسجيل الدخول" لتسجيل الدخول.',
                'Դուք մուտք չեք գործել: Մուտք գործելու համար խնդրում ենք ասել «մուտք գործել»:'])
            print('\nBOT:', utterance)
            dispatcher.utter_message(utterance)
        
        return []



class ActionCheckWeather(Action):
    def name(self):
        return 'action_check_weather'

    def alpha2_to_name(self, alpha2):
        try:
            name = pycountry.countries.get(alpha_2=alpha2).name
            return name
        except Exception as e:
            print(f'\n> ActionCheckWeather.alpha2_to_name: [ERROR] {e}')
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

        except Exception as e:
            print(f'\n> ActionCheckWeather.call_api: [ERROR] {e}')
            return {'response': False}        


    def utter_weather(self, city_name):
        result = self.call_api(city_name)

        if result['response']:
            if result['code'] == '200':
                return 'Temperature is currently {} °C in {}{}.'.format(result['temperature'], result['city'], result['country'])
            if result['code'] == '404':
                return 'Sorry, I could not find a city or country named {}.'.format(city_name.title())
            return 'Sorry, there was an error looking for the weather in {} (Error {}).'.format(city_name.title(), result['code'])
        return f'Sorry, the weather server is not responding.'

    
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)

        latest = tracker.latest_message
        
        if latest['entities']:
            for blob in latest['entities']: # To get it as a slot: tracker.get_slot('city_name')
                if blob['entity'] == 'city_name':
                    city_name = blob['value']
                    result = self.utter_weather(city_name)
                    print('\nBOT:', result)
                    dispatcher.utter_message(result)
                return [SlotSet('city_name', city_name)]
        
        elif tracker.slots['city_name']:
            city_name  = tracker.slots['city_name']
            result = self.utter_weather(city_name)
            print('\nBOT:', result)
            dispatcher.utter_message(result)
        
        else:
            utterance = 'Please provide a city or country to check the weather.'
            print('\nBOT:', utterance)
            dispatcher.utter_message(utterance)
        
        return []



class ActionOutOfScope(Action):
    def name(self):
        return 'action_out_of_scope'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)

        latest = tracker.latest_message
        intent = latest['intent']['name']
        query  = tracker.slots['out_of_scope']

        if intent == 'out_of_scope':
            text = 'Sorry, I don\'t understand. Do you want me to search that on Google?'
            print('\nBOT:', text)
            dispatcher.utter_message(text)
            return [SlotSet('out_of_scope', latest['text'])]

        if intent == 'affirm' and query is not None:
            try:
                text = 'Here are the top results:'
                urls = [url for url in googlesearch.search(
                    query = query,
                    tld = 'com.lb',
                    lang = 'en',
                    num = 5,
                    stop = 5,
                    pause = 1,
                    extra_params = {'filter': '0'})]
                print('\nBOT:', text)
                dispatcher.utter_message(text)

                for url in urls:
                    dispatcher.utter_message(str(url))
            except Exception as e:
                dispatcher.utter_message('Sorry, I could not comlete the search.\n' + str(e))
                print('> ActionOutOfScope [ERROR] ' + str(e))
            return [SlotSet('out_of_scope', None)]
            
        if (intent == 'deny' or intent == 'stop') and query is not None:
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