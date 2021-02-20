import requests
import googlesearch
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

class ActionFetchQuota(Action):
    def name(self) -> Text:
        return 'action_fetch_quota'

def run(self, dispatcher, tracker, domain):
        print('='*100)
        print(str(tracker.latest_message))
        
        pokemon_name = None

        for blob in tracker.latest_message['entities']:            
            if blob['entity'] == 'pokemon_name':
                name = blob['value'].title()
                if name.lower() in self.knowledge:
                    dispatcher.utter_message(text=f'Yes, {name} is a Pokémon.')
                    return [SlotSet('pokemon_name', name)]
                else:
                    dispatcher.utter_message(text=f'{name} is not a Pokémon.')
        
        if pokemon_name:
            return [SlotSet('pokemon_name', name)]
        else:
            return []



class ActionCheckExistence(Action):
    knowledge = Path('data/lookups/pokemon_name.txt').read_text().split('\n')

    def name(self) -> Text:
        return 'action_check_existence'

    def run(self, dispatcher, tracker, domain):
        print('='*100)
        print(str(tracker.latest_message))

        latest = tracker.latest_message
        
        if latest['entities']:
            for blob in latest['entities']: # To get it as a slot: tracker.get_slot('city_name')
                if blob['entity'] == 'person_name':
                    person_name = blob['value']
                    result = self.utter_weather(person_name)
                    dispatcher.utter_message(result)
                return [SlotSet('person_name', person_name)]
        
        elif tracker.slots['person_name']:
            person_name  = tracker.slots['person_name']
            result = self.utter_weather(person_name)
            dispatcher.utter_message(result)
        
        else:
            dispatcher.utter_message('Please provide a city or country to check the weather.')
        
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
        print('='*100)
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
        print('='*100)
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