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


class ActionSubmitFormLogIn(Action):
    def name(self):
        return 'action_submit_form_log_in'


    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        if tracker.get_slot('loggedin'):
            username = tracker.get_slot('username')
            login_type = tracker.get_slot('login_type').replace('_', ' ')

            text = _common.get_text_from_lang(
                tracker,
                ['You are logged in with {} being {}'.format(login_type, username),
                'Vous êtes connecté avec {} étant {}'.format(login_type, username),
                'لقد قمت بتسجيل الدخول {} يجري {}'.format(login_type, username),
                'Դուք մուտք եք գործել ՝{} լինելով {}'.format(login_type, username)])            
            print('\nBOT:', text)
            dispatcher.utter_message(text)

        return []



class ActionSubmitFormTroubleshootInternet(Action):
    def name(self):
        return 'action_submit_form_troubleshoot_internet'


    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)

        text = ''
        slots_to_reset = list(domain['forms']['form_troubleshoot_internet'].keys())
        exceptions = ['username', 'ti_form_completed']
        events = _common.reset_slots(tracker, slots_to_reset, exceptions)
        events.append(SlotSet('ti_form_completed', False))

        if (tracker.get_slot('tik_has_line') is not None) and (tracker.get_slot('username') is not None): # User has completed the form
            username   = tracker.get_slot('username').title()

            text = _common.get_text_from_lang(
                tracker,
                ['A case was created for {}.'.format(username),
                'Un dossier a été créé pour {}.'.format(username),
                'تم إنشاء حالة لـ {}.'.format(username),
                'Գործ ստեղծվեց {} - ի համար:'.format(username)]) + '\n'

        
        text += _common.get_text_from_lang(tracker, _common.text_anything_else)
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return events
