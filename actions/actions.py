import json
import requests

from pathlib import Path
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase



class ActionCheckExistence(Action):
    knowledge = Path("data/pokenames.txt").read_text().split("\n")

    def name(self) -> Text:
        return "action_check_existence"

    #def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
    def run(self, dispatcher, tracker, domain):
        print('='*100)
        pokemon_name = None

        for blob in tracker.latest_message['entities']:
            print(str(tracker.latest_message) + '\n')
            #dispatcher.utter_message(text=str(blob))
            
            if blob['entity'] == 'pokemon_name':
                name = blob['value'].title()
                if name.lower() in self.knowledge:
                    dispatcher.utter_message(text=f"Yes, {name} is a pokemon.")
                    return [SlotSet('pokemon_name', name)]
                else:
                    dispatcher.utter_message(text=f"I do not recognize {name}, are you sure it is correctly spelled?")
        
        if pokemon_name:
            return [SlotSet('pokemon_name', name)]
        else:
            return []



class ActionCheckWeather(Action):
    def name(self):
        return "action_check_weather"

    def get(self, city_name):
        api_key = "d24a63d18af95420958d7bb8b5839016"
        url = "http://api.openweathermap.org/data/2.5/weather?"+ "appid=" + api_key + "&q=" + city_name
        
        response = requests.get(url).json()
        code = str(response["cod"])
        
        if code == "200": 
            return "Temperature is currently " + str(round(response["main"]["temp"] - 273.15, 1)) + " °C in " + city_name.title() + "."
        elif code == "404":
            return "Sorry, I could not find " + city_name.title() + "."
        else: 
            return "Sorry, there was an error (" + code + ")."

    def run(self, dispatcher, tracker, domain):
        print('='*100)
        city_name = None
        
        for blob in tracker.latest_message['entities']: # To get it as a slot: tracker.get_slot('city_name')
            print(str(tracker.latest_message) + '\n')
            #dispatcher.utter_message(text=str(blob))

            if blob['entity'] == 'city_name':
                city_name = blob['value']
                result = self.get(city_name)
                dispatcher.utter_message(result)
        
        if city_name:
            return [SlotSet('city_name', city_name)]
        else:
            return []
