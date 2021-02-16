import json
import requests
import time
import googlesearch
import os

from pathlib import Path
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase
from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase

####################################################################################################

class ActionCheckExistence(Action):
    knowledge = Path('data/pokenames.txt').read_text().split('\n')

    def name(self) -> Text:
        return 'action_check_existence'

    #def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
    def run(self, dispatcher, tracker, domain):
        print('='*100)
        print(str(tracker.latest_message) + '\n')
        
        pokemon_name = None

        for blob in tracker.latest_message['entities']:            
            if blob['entity'] == 'pokemon_name':
                name = blob['value'].title()
                if name.lower() in self.knowledge:
                    dispatcher.utter_message(text=f'Yes, {name} is a pokemon.')
                    return [SlotSet('pokemon_name', name)]
                else:
                    dispatcher.utter_message(text=f'I do not recognize {name}, are you sure it is correctly spelled?')
        
        if pokemon_name:
            return [SlotSet('pokemon_name', name)]
        else:
            return []



class ActionCheckWeather(Action):
    def name(self):
        return 'action_check_weather'

    def get(self, city_name):
        api_key = 'd24a63d18af95420958d7bb8b5839016'
        url = f'http://api.openweathermap.org/data/2.5/weather?appid={api_key}&q={city_name}'
        
        response = requests.get(url).json()
        code = str(response['cod'])
        print(code, city_name)
        
        if code == '200': 
            temperature = str(round(response['main']['temp'] - 273.15, 1))
            return f'Temperature is currently {temperature} °C in {city_name.title()}.'
        #elif code == '404':
        #    return 'Sorry, I could not find a city or country named {city_name.title()}.'
        else: 
            return f"Sorry, there was an error ({code})."

    def run(self, dispatcher, tracker, domain):
        print('='*100)
        print(str(tracker.latest_message) + '\n')

        latest = tracker.latest_message
        
        if latest['entities']:
            city_name = None

            for blob in latest['entities']: # To get it as a slot: tracker.get_slot('city_name')
                if blob['entity'] == 'city_name':
                    city_name = blob['value']
                    result = self.get(city_name)
                    dispatcher.utter_message(result)
            
            if city_name:
                return [SlotSet('city_name', city_name)]
        
        else:
            dispatcher.utter_message('Sorry, I did not catch that, could you rephrase?')
        
        return []



class ActionOutOfScope(Action):
    def name(self):
        return "action_out_of_scope"

    def run(self, dispatcher, tracker, domain):
        print('='*100)
        print(str(tracker.latest_message) + '\n')

        latest = tracker.latest_message
        intent = latest['intent']['name']
        
        if intent == 'out_of_scope':
            text = latest['text']
            dispatcher.utter_message('Do you want me to search "{}" on Google?'.format(text))
            return [SlotSet('out_of_scope', text)]

        elif intent == 'affirm':
            try:
                query = tracker.slots['out_of_scope']
                reply = 'Here are the top results for "{}":\n'.format(query)
                for url in [url for url in googlesearch.search(query=query, tld='com.lb', lang='en', num=1, stop=5, pause=0)]:
                    reply += url + '\n'
                dispatcher.utter_message(reply[:-1])
            except Exception as e:
                dispatcher.utter_message('Sorry, I could not comlete the search.\n' + str(e))
                print('[ERROR] ' + str(e))

            return []
            
        else:
            dispatcher.utter_message('Okay.')
            return []

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