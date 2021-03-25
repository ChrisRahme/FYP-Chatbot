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

class ValidateFormLogIn(FormValidationAction):
    def name(self):
        return 'validate_form_log_in'

    
    # Custom Slot Mappings: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        required_slots = ['username', 'password']
        return required_slots


    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_username(self, value, dispatcher, tracker, domain):
        return await _common.global_validate_username(value, dispatcher, tracker, domain)


    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_password(self, value, dispatcher, tracker, domain):
        return await _common.global_validate_password(value, dispatcher, tracker, domain)



class ValidateFormTroubleshootInternet(FormValidationAction):
    def name(self):
        return 'validate_form_troubleshoot_internet'


    async def validate_username(self, value, dispatcher, tracker, domain):
        slots = await _common.global_validate_username(value, dispatcher, tracker, domain)
        slots['ti_form_completed'] = True
        return 

    
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        
        text_if_works = _common.get_text_from_lang(
            tracker, ['Great! I\'m glad that it works now.', 'Génial!', 'رائع!', 'Հոյակապ:']
            )# + '\n' + _common.get_text_from_lang(tracker, text_anything_else)
        checkpoint = False

        required_slots = ['tia_noise']
        if tracker.get_slot('tia_noise'): # There is noise on the line, ask to contact Ogero
            required_slots.append('tiaa_noise')
            if tracker.get_slot('tiaa_noise'): # The noise is gone and the problem is fixed, stop
                print('\nBOT:', text_if_works)
                dispatcher.utter_message(text_if_works)
            else: # The noise is gone but the problem is not fixed, continue
                checkpoint = True
        else: # There is no noise on the line, continue
            checkpoint = True

        if checkpoint: # There is no noise on the line, continue
            required_slots.append('tib_modem_on')
            if tracker.get_slot('tib_modem_on'): # The modem is on and it works, stop
                print('\nBOT:', text_if_works)
                dispatcher.utter_message(text_if_works)
            else: # The modem is on and it doesn't work, continue
                required_slots.append('tic_modem_green')
                if tracker.get_slot('tic_modem_green'): # The LED is green and it works, stop
                    print('\nBOT:', text_if_works)
                    dispatcher.utter_message(text_if_works)
                else: # The LED is green and it doesn't work, continue
                    required_slots.extend(['tid_nb_phones', 'tie_nb_sockets', 'tif_splitter_installed'])
                    if tracker.get_slot('tif_splitter_installed'): # The splitter is properly installed on all phones and modems and it works, stop
                        print('\nBOT:', text_if_works)
                        dispatcher.utter_message(text_if_works)
                    else: # The splitter is properly installed on all phones and modems and it doesn't work, continue
                        required_slots.append('tig_rj_plugged')
                        if tracker.get_slot('tig_rj_plugged'): # The RJ11 is plugged in and it works, stop
                            print('\nBOT:', text_if_works)
                            dispatcher.utter_message(text_if_works)
                        else: # The RJ11 is plugged in and it doesn't work, continue
                            required_slots.append('tih_other_plug')
                            if tracker.get_slot('tih_other_plug'): # The modem was plugged somewhere else and it works, stop
                                print('\nBOT:', text_if_works)
                                dispatcher.utter_message(text_if_works)
                            else: # The modem was plugged somewhere else and it doesn't work, continue
                                required_slots.append('tii_other_modem')
                                if tracker.get_slot('tii_other_modem'): # Another modem is plugged in and it works, stop
                                    print('\nBOT:', text_if_works)
                                    dispatcher.utter_message(text_if_works)
                                else: # Another modem is plugged in and it doesn't work, continue
                                    required_slots.extend(['tij_has_pbx', 'tik_has_line', 'username'])
        
        #if required_slots == ['tia_noise', 'tiaa_noise'] and tracker.get_slot('tia_noise'): # To not repeat it multiple times
        #    print('\nBOT:', text_contact_ogero)
        #    dispatcher.utter_message(text_contact_ogero)

        return required_slots
