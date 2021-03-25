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

class ActionSessionStart(Action):
    def name(self):
        return 'action_session_start'

    @staticmethod
    def fetch_slots(tracker):
        slots = []
        slots_to_keep = []
        
        for slot_name in slots_to_keep:
            slot_value = tracker.get_slot(slot_name)
            if slot_value is not None:
                slots.append(SlotSet(key = slot_name, value = slot_value))

        return slots

    def run(self, dispatcher, tracker, domain):
        _common.announce(self)
        print(tracker.sender_id)

        events = [SessionStarted()]
        events.extend(self.fetch_slots(tracker))
        #events.append(ActionExecuted('action_utter_ask_language'))
        events.append(ActionExecuted('action_listen'))

        _common.conversation_data[tracker.sender_id] = {'password_tries': 0}
        
        return events