import requests
import googlesearch
import mysql.connector
import pycountry

import json
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
# HELPER CLASSES & FUNCTIONS                                                                       #
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
            host     = '194.126.17.114',
            database = 'rasa_db',
            user     = 'rasaq', # granted all privileges on rasa_db.* to rasaq@%
            password = 'rasa')

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
        print(f'\n> get_lang: [ERROR] {e}')
        return 'English'



def get_lang_index(tracker):
    return lang_list.index(get_lang(tracker))



def get_text_from_lang(tracker, utter_list = []):
    lang_index = get_lang_index(tracker)

    if not utter_list: # No text was given for any language
        utter_list.append('[NO TEXT DEFINED]')

    if lang_index >= len(utter_list): # No text defined for current language
        lang_index = 0

    return utter_list[lang_index]



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



####################################################################################################
# DEFAULT ACTIONS                                       https://rasa.com/docs/rasa/default-actions #
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
        announce(self)
        print(tracker.sender_id)

        events = [SessionStarted()]
        events.extend(self.fetch_slots(tracker))
        #events.append(ActionExecuted('action_utter_change_language'))
        events.append(ActionExecuted('action_listen'))

        conversation_data[tracker.sender_id] = {'password_tries': 0}
        
        return events



####################################################################################################
# SLOTS                                                                                            #
####################################################################################################



class ActionAskUsername(Action):
    def name(self):
        return 'action_ask_username'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please enter your Username, L Number, or Phone Number, or press "🚫" to stop.',
            'Veuillez entrer votre nom d\'utilisateur, L Number, ou Numéro de Téléphone, ou appuyez sur "🚫" pour arrêter.',
            'الرجاء إدخال اسم المستخدم أو رقم L أو رقم الهاتف ، أو اضغط على "🚫" للإيقاف.',
            'Կանգնեցնելու համար խնդրում ենք մուտքագրել ձեր օգտանունը, L համարը կամ հեռախոսահամարը կամ սեղմել «🚫»:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = button_stop_emoji)
        return []



class ActionAskPassword(Action):
    def name(self):
        return 'action_ask_password'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please enter your password.',
            'S\'il vous plaît entrez votre mot de passe.',
            '.(password) من فضلك أدخل رقمك السري',
            'Խնդրում ենք մուտքագրել ձեր գաղտնաբառը (username).'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = button_stop_emoji)
        return []



class ActionAskTiaNoise(Action):
    def name(self):
        return 'action_ask_tia_noise'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Is there noise on the line where the ADSL number is connected?',
            'Y a-t-il du bruit sur la ligne où le numéro ADSL est connecté?',
            'هل توجد ضوضاء على الخط الموصل به رقم ADSL؟',
            'Արդյո՞ք աղմուկ կա այն գծի վրա, որտեղ միացված է ADSL համարը:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



class ActionAskTiaaNoise(Action):
    def name(self):
        return 'action_ask_tiaa_noise'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please try to contact Ogero on 1515 to resolve the noise on the line.',
            'Veuillez essayer de contacter Ogero au 1515 pour résoudre le bruit sur la ligne.',
            'يرجى محاولة الاتصال بـ Ogero على 1515 لحل الضوضاء على الخط.',
            'Խնդրում ենք փորձել կապվել Ogero- ի հետ 1515-ին `գծի աղմուկը լուծելու համար:'
            ]) + '\n' + get_text_from_lang(
            tracker,
            ['After you resolved the noise issue with Ogero, restart the modem.',
            'Y a-t-il du bruit sur la ligne où le numéro ADSL est connecté?',
            'هل توجد ضوضاء على الخط الموصل به رقم ADSL؟',
            'Արդյո՞ք աղմուկ կա այն գծի վրա, որտեղ միացված է ADSL համարը:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



class ActionAskTibModemOn(Action):
    def name(self):
        return 'action_ask_tib_modem_on'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please make sure your modem is turned on.',
            'Veuillez vous assurer que votre modem est allumé.',
            'يرجى التأكد من تشغيل المودم الخاص بك.',
            'Համոզվեք, որ ձեր մոդեմը միացված է:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



class ActionAskTicModemGreen(Action):
    def name(self):
        return 'action_ask_tic_modem_green'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please reboot your modem, wait 30 seconds, and make sure the power LED on your modem is green.',
            'Veuillez redémarrer votre modem, attendez 30 secondes et assurez-vous que la DEL (LED) de votre modem est verte.',
            'يُرجى إعادة تشغيل المودم الخاص بك ، وانتظر 30 ثانية ، وتأكد من أن مصباح الطاقة (LED) الموجود في المودم الخاص بك أخضر.',
            'Վերաբեռնեք ձեր մոդեմը, սպասեք 30 վայրկյան և համոզվեք, որ ձեր մոդեմի էլեկտրական LED- ը կանաչ է:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



class ActionAskTidNbPhones(Action):
    def name(self):
        return 'action_ask_tid_nb_phones'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['How many faxes and phones do you have?',
            'Combien de fax et de téléphones fixes avez-vous?',
            'كم عدد الفاكسات والهواتف التي لديك؟',
            'Քանի՞ ֆաքս և հեռախոս ունեք:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = button_stop_emoji)
        return []



class ActionAskTieNbSockets(Action):
    def name(self):
        return 'action_ask_tie_nb_sockets'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['How many phone wall sockets do you have?',
            'Combien de prises téléphoniques murales avez-vous?',
            'كم عدد مآخذ توصيل الحائط بالهاتف لديك؟',
            'Քանի՞ հեռախոսի պատի վարդակ ունեք:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = button_stop_emoji)
        return []



class ActionAskTifSplitterInstalled(Action):
    def name(self):
        return 'action_ask_tif_splitter_installed'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please use the following picture to check if your splitter is correctly installed on all your fixed phones and modems.',
            'Veuillez utiliser l\'image suivante pour vérifier si votre répartiteur est correctement installé sur tous vos téléphones fixes et modems.',
            'الرجاء استخدام الصورة التالية للتحقق مما إذا كان جهاز التقسيم مثبتًا بشكل صحيح على جميع الهواتف الثابتة وأجهزة المودم.',
            'Խնդրում ենք օգտագործել հետևյալ նկարը ՝ ստուգելու համար, թե արդյոք ձեր բաժանարարը ճիշտ է տեղադրված ձեր բոլոր ֆիքսված հեռախոսների և մոդեմների վրա:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji, image = 'https://i.imgur.com/aV0uxGx.png')
        return []



class ActionAskTigRjPlugged(Action):
    def name(self):
        return 'action_ask_tig_rj_plugged'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Please make sure the phone cable plugged in the modem is RJ11 and not the Ethernet port.',
            'Veuillez vous assurer que le câble téléphonique branché sur le modem est RJ11 et non le port Ethernet.',
            'يرجى التأكد من أن كبل الهاتف المتصل بالمودم هو RJ11 وليس منفذ Ethernet.',
            'Խնդրում ենք համոզվեք, որ մոդեմի մեջ միացված հեռախոսի մալուխը RJ11 է և ոչ թե Ethernet պորտ:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji, image = 'https://i.imgur.com/9aUcYs5.png')
        return []



class ActionAskTihOtherPlug(Action):
    def name(self):
        return 'action_ask_tih_other_plug'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Try to plug the modem into another socket.',
            'Essayez de brancher le modem sur une autre prise.',
            'حاول توصيل المودم بمقبس آخر.',
            'Փորձեք մոդեմը միացնել մեկ այլ վարդակի:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work) + ' (' + get_text_from_lang(
                tracker,
                ['Press "no" if you can\'t use another socket.',
                'Appuyez sur "non" si vous ne pouvez pas utiliser une autre prise.',
                'اضغط على "لا" إذا كنت لا تستطيع استخدام مقبس آخر.',
                'Սեղմեք «ոչ» -ը, եթե այլ վարդակից չեք կարող օգտվել:'
            ]) + ')'
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



class ActionAskTiiOtherModem(Action):
    def name(self):
        return 'action_ask_tii_other_modem'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Try to use another modem.',
            'Essayez d\'utiliser un autre modem.',
            'حاول استخدام مودم آخر.',
            'Փորձեք օգտագործել մեկ այլ մոդեմ:'
            ]) + '\n' + get_text_from_lang(tracker, text_does_it_work) + ' (' + get_text_from_lang(
                tracker,
                ['Press "no" if you can\'t use another modem.',
                'Appuyez sur "non" si vous ne pouvez pas utiliser un autre modem.',
                'اضغط على "لا" إذا كنت لا تستطيع استخدام مودم آخر.',
                'Սեղմեք «ոչ» -ը, եթե այլ մոդեմ չեք կարող օգտագործել:'
            ]) + ')'
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



class ActionAskTijHasPbx(Action):
    def name(self):
        return 'action_ask_tij_has_pbx'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Do you have a PBX?',
            'Avez-vous un PBX?',
            'هل لديك مقسم؟',
            'Ունե՞ք PBX:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji, image = 'https://techextension.com/images/cloud_pbx_connections.png')
        return []



class ActionAskTikHasLine(Action):
    def name(self):
        return 'action_ask_tik_has_line'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Do you have an Internet line?',
            'Avez-vous une ligne Internet?',
            'هل لديك خط انترنت؟',
            'Ինտերնետային գիծ ունե՞ք:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons_yes_no_stop_emoji)
        return []



####################################################################################################
# FORM VALIDATION ACTIONS                                                                          #
####################################################################################################



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



class ValidateFormLogIn(FormValidationAction):
    def name(self):
        return 'validate_form_log_in'

    
    # Custom Slot Mappings: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        required_slots = ['username', 'password']
        return required_slots


    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_username(self, value, dispatcher, tracker, domain):
        return await global_validate_username(value, dispatcher, tracker, domain)


    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_password(self, value, dispatcher, tracker, domain):
        if not tracker.get_slot('loggedin'):
            username = tracker.get_slot('username')
            password = tracker.get_slot('password')
            login_type = tracker.get_slot('login_type')

            db = DatabaseConnection()
            count = db.count('user_info', f"{login_type} = '{username}' AND Password = '{password}'")
            db.disconnect()

            if count == 1:
                print('\n> validate_password: Login with', username)
                return {'password': password, 'loggedin': True}

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



class ValidateFormTroubleshootInternet(FormValidationAction):
    def name(self):
        return 'validate_form_troubleshoot_internet'


    async def validate_username(self, value, dispatcher, tracker, domain):
        slots = await global_validate_username(value, dispatcher, tracker, domain)
        slots['ti_form_completed'] = True
        return 

    
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        announce(self, tracker)
        
        text_if_works = get_text_from_lang(
            tracker, ['Great! I\'m glad that it works now.', 'Génial!', 'رائع!', 'Հոյակապ:']
            ) + '\n' + get_text_from_lang(tracker, text_anything_else)
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



####################################################################################################
# FORM SUBMIT ACTIONS                                                                              #
####################################################################################################



class ActionSubmitFormLogIn(Action):
    def name(self):
        return 'action_submit_form_log_in'


    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        if tracker.get_slot('loggedin'):
            username = tracker.get_slot('username')
            login_type = tracker.get_slot('login_type').replace('_', ' ')

            text = get_text_from_lang(
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
        announce(self, tracker)

        text = ''
        slots_to_reset = list(domain['forms']['form_troubleshoot_internet'].keys())
        exceptions = ['username', 'ti_form_completed']
        events = reset_slots(tracker, slots_to_reset, exceptions)
        events.append(SlotSet('ti_form_completed', False))

        if (tracker.get_slot('tik_has_line') is not None) and (tracker.get_slot('username') is not None): # User has completed the form
            username   = tracker.get_slot('username').title()

            text = get_text_from_lang(
                tracker,
                ['A case was created for {}.'.format(username),
                'Un dossier a été créé pour {}.'.format(username),
                'تم إنشاء حالة لـ {}.'.format(username),
                'Գործ ստեղծվեց {} - ի համար:'.format(username)]) + '\n'

        
        text += get_text_from_lang(tracker, text_anything_else)
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return events



####################################################################################################
# RESPONSE UTTERANCES                                                                              #
####################################################################################################



class ActionUtterGreet(Action):
    def name(self):
        return 'action_utter_greet'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        response = get_response_from_lang(tracker, 'utter_greet')
        buttons  = get_buttons_from_lang(
            tracker,
            [['Wireless', 'Internet', 'DSL Internet', 'CableVision TV'],
            ['Sans Fil', 'Internet', 'Internet DSL', 'CableVision TV'],
            ['لاسلكي','إنترنت','DSL إنترنت','تلفزيون الكابل'],
            ['Անլար', 'Ինտերնետ', 'DSL ինտերնետ', 'CableVision TV']],
            [
                '/inform_service_type{"service_type": "wireless"}',
                '/inform_service_type{"service_type": "internet"}',
                '/inform_service_type{"service_type": "dsl"}',
                '/inform_service_type{"service_type": "cablevision"}'
            ])
        print('\nBOT: {utter_greet}', buttons)
        dispatcher.utter_message(response = response, buttons = buttons)
        return []



class ActionUtterGoodbye(Action):
    def name(self):
        return 'action_utter_goodbye'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        dispatcher.utter_message(response = get_response_from_lang(tracker, 'utter_goodbye'))
        return []
            


class ActionUtterYoureWelcome(Action):
    def name(self):
        return 'action_utter_youre_welcome'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        response = get_response_from_lang(tracker, 'utter_youre_welcome')
        print('\nBOT:', response)
        dispatcher.utter_message(response = response)
        return []



####################################################################################################
# TEXT UTTERANCES                                                                                  #
####################################################################################################



class ActionUtterChangeLanguage(Action):
    def name(self):
        return 'action_utter_change_language'
    

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        
        text = get_text_from_lang(
            tracker,
            ['Choose a language:',
            'Choisissez une langue:',
            ':اختر لغة',
            'Ընտրեք լեզու ՝'])

        buttons = [ # https://forum.rasa.com/t/slots-set-by-clicking-buttons/27629
            {'title': 'English',  'payload': '/set_language{"language": "English"}'},
            {'title': 'Français', 'payload': '/set_language{"language": "French"}'},
            {'title': 'عربي',     'payload': '/set_language{"language": "Arabic"}'},
            {'title': 'հայերեն',  'payload': '/set_language{"language": "Armenian"}'}
        ]
       
        print('\nBOT:', text, buttons)
        dispatcher.utter_message(text = text, buttons = buttons)

        return []



class ActionUtterRecoverCredentials(Action):
    def name(self):
        return 'action_utter_recover_credentials'


    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        url = 'https://myaccount.idm.net.lb/_layouts/15/IDMPortal/ManageUsers/ResetPassword.aspx'
        url = '\n\n' + url

        text = get_text_from_lang(
            tracker,
            ['If you need help recovering your IDM ID or your password, click on the link below:',
            'Si vous avez besoin d\'aide pour récupérer votre ID IDM ou votre mot de passe, cliquez sur le lien ci-dessous:',
            'لا مشكلة. إذا كنت بحاجة إلى مساعدة في استعادة معرّف IDM أو كلمة مرورك ، فانقر على الرابط أدناه:',
            'Ոչ մի խնդիր. Եթե ձեր IDM ID- ն կամ գաղտնաբառն վերականգնելու համար օգնության կարիք ունեք, կտտացրեք ստորև նշված հղմանը.'])
        text = text + '\n' + url
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return []



class ActionUtterAccountTypes(Action):
    def name(self):
        return 'action_utter_account_types'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Which account type are you asking about?',
            'Quel type de compte avez-vous?',
            'ما نوع الحساب الذي تسأل عنه؟',
            'Հաշվի ո՞ր տեսակի մասին եք հարցնում:'])
        buttons  = get_buttons_from_lang(
            tracker,
            [['Consumer / Residential', 'Small Business', 'Bank'],
            ['Consommateur / Résidentiel', 'Petite Entreprise', 'Banque'],
            ['استهلاكي / سكني', 'أعمال صغيرة', 'مصرف'],
            ['Սպառող / բնակելի', 'Փոքր բիզնես', 'Բանկ']],
            [
                '/inform_account_type{"account_type": "consumer"}',
                '/inform_account_type{"account_type": "business"}',
                '/inform_account_type{"account_type": "bank"}'
            ]
        )
        print('\nBOT:', text, buttons)
        dispatcher.utter_message(text = text, buttons = buttons)
        return []



class ActionUtterTopicTypes(Action):
    def name(self):
        return 'action_utter_topic_types'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            ['Choose a topic to chat about:',
            'Choisissez un sujet de discussion:',
            'اختر موضوعًا للمناقشة:',
            'Ընտրեք քննարկման թեմա:'])
        buttons  = get_buttons_from_lang(
            tracker,
            [['Billing, Plans & Setup', 'Payments', 'Shopping', 'Order Status', 'Moving or Changing Service', 'Troubleshooting & Repairs', 'Online Account & Sign-in Help'],
            ['Facturation, Plans et Configuration de l\'Équipement', 'Paiements', 'Achats', 'Statut de Commande', 'Déménagement ou Changement de Service', 'Dépannage et Réparations', 'Compte en Ligne et Aide à la Connexion'],
            ['إعداد الفواتير والخطط والمعدات', 'المدفوعات', 'التسوق', 'حالة الطلب', 'نقل أو تغيير الخدمة', 'استكشاف الأخطاء وإصلاحها والإصلاحات', 'حساب عبر الإنترنت وتعليمات تسجيل الدخول'],
            ['Վճարների, պլանների և սարքավորումների տեղադրում', 'Վճարներ', 'Գնումներ', 'Պատվերի կարգավիճակ', 'Շարժվող կամ փոխելու ծառայություն', 'Խնդիրների լուծում և վերանորոգում', 'Առցանց հաշվի և մուտքի օգնություն']],
            [
                '/inform_topic_type{"topic_type": "billing"}',
                '/inform_topic_type{"topic_type": "payments"}',
                '/inform_topic_type{"topic_type": "shopping"}',
                '/inform_topic_type{"topic_type": "order"}',
                '/inform_topic_type{"topic_type": "changing"}',
                '/inform_topic_type{"topic_type": "troubleshooting"}',
                '/inform_topic_type{"topic_type": "account"}'
            ])
        print('\nBOT:', text, buttons)
        dispatcher.utter_message(text = text, buttons = buttons)
        return []



class ActionUtterTopicSamples(Action):
    def name(self):
        return 'action_utter_topic_samples'


    def get_sample_questions(self, topic_type, account_type, service_type):
        examples_en = [
            '[THIS IS JUST AN EXAMPLE.]',
            '[IT WILL PROVIDE QUESTIONS]',
            '[GIVEN THE CHOICES YOU MADE.]',
            '[TRY THE FOLLOWING TOPICS:]',
            '[Billing, Payments, Account, Troubleshooting]'
        ]
        examples_fr = examples_en
        examples_ar = examples_en
        examples_hy = examples_en

        if topic_type == 'billing' or topic_type == 'payment':
            examples_en = [
                'Where can I purchase a prepaid card?',
                'How can I get my bill?',
                'How can I check my bill?',
                'What are the available payment methods?',
                'How can I change my payment method?'
            ]
            examples_fr = examples_en
            examples_ar = examples_en
            examples_hy = examples_en

        elif topic_type == 'account':
            examples_en = [
                'I forgot my username',
                'I don\'t know my password',
                'I\'m having trouble logging in'
            ]
            examples_fr = [
                'J\'ai oublié mon nom d\'utilisateur',
                'Je ne connais pas mon mot de passe',
                'Je n\'arrive pas à m\'identifier'
            ]
            examples_ar = [
                'لقد نسيت اسم المستخدم',
                'نسيت كلمة المرور',
                'أحتاج إلى مساعدة في تسجيل الدخول'
            ]
            examples_hy = [
                'Մոռացել եմ օգտանունս',
                'Ես մոռացել եմ իմ գաղտնաբառը',
                'ինձ անհրաժեշտ է մուտք գործել'
            ]

        elif topic_type == 'troubleshooting':
            examples_en = [
                'I don\'t have Internet',
                'My Internet is slow'
            ]
            examples_fr = [
                'Je n\'ai pas Internet',
                'Ma connexion est lente'
            ]
            examples_ar = examples_en
            examples_hy = examples_en

        return examples_en, examples_fr, examples_ar, examples_hy


    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        service_type = tracker.get_slot('service_type') # wireless - internet - dsl - cablevision
        account_type = tracker.get_slot('account_type') # consumer - business - bank
        topic_type   = tracker.get_slot('topic_type')   # billing - payments - shopping - order - changing - troubleshooting - account

        examples_en, examples_fr, examples_ar, examples_hy = self.get_sample_questions(topic_type, account_type, service_type)

        examples_en = '\n- '.join(examples_en)
        examples_fr = '\n- '.join(examples_fr)
        examples_ar = '\n- '.join(examples_ar)
        examples_hy = '\n- '.join(examples_hy)

        text_en = (
            'You chose:'
            f'\n- Service type: {service_type}'
            f'\n- Account type: {account_type}'
            f'\n- Topic: {topic_type}'
            f'\n\nYou can say things like:'
            f'\n- {examples_en}')
        text_fr = (
            'Vous avez choisi:'
             f'\n- Type de service: {service_type}'
             f'\n- Type de compte: {account_type}'
             f'\n- Topic: {topic_type}'
            f'\n\nVous pouvez demander:'
            f'\n- {examples_fr}')
        text_ar = (
            'اخترت:'
            f'\n- نوع الخدمة: {service_type}'
            f'\n- نوع الحساب: {account_type}'
            f'\n- الموضوع: {topic_type}'
            f'\n\nتستطيع أن تسأل:'
            f'\n- {examples_ar}')
        text_hy = (
            'Դուք ընտրեցիք:'
            f'\n- ծառայության տեսակը: {service_type}'
            f'\n- Հաշվի տեսակը: {account_type}'
            f'\n- Թեմա: {topic_type}'
            f'\n\nԴու կարող ես հարցնել:'
            f'\n- {examples_hy}')

        text = get_text_from_lang(tracker, [text_en, text_fr, text_ar, text_hy])            
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return []



####################################################################################################
# ACTIONS                                                                                          #
####################################################################################################



class ActionSetLanguage(Action):
    def name(self) -> Text:
        return 'action_set_language'
    

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)

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
            utterance = 'I only understand English, French, Arabic, and Armenian. The language is now English.'
        
        dispatcher.utter_message(utterance)
        
        if not tracker.get_slot('service_type'):
            return [FollowupAction('action_utter_greet')]
        return []



class ActionFetchQuota(Action):
    def name(self) -> Text:
        return 'action_fetch_quota'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)

        if tracker.get_slot('loggedin') or tracker.get_slot('password') == 'secret':
            results    = None
            username   = tracker.get_slot('username')
            login_type = tracker.get_slot('login_type')

            try:
                db = DatabaseConnection()
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
                    utterance = get_text_from_lang(
                        tracker,
                        ['You spent {} GB of your unlimited quota this month.'.format(consumption),
                        'Vous avez dépensé {} Go de votre quota illimité pour ce mois.'.format(consumption),
                        '.لقد أنفقت {} غيغابايت من حصتك غير المحدودة هذا الشهر'.format(consumption),
                        'Դուք անցկացրել {} ԳԲ ձեր անսահման քվոտայի այս ամսվա.'.format(consumption)])
                    print('\nBOT:', utterance)
                    dispatcher.utter_message(utterance)
                else:
                    ratio = consumption*100/quota
                    utterance = get_text_from_lang(
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
            utterance = get_text_from_lang(
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
        announce(self, tracker)

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
        announce(self, tracker)

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
# SILENT ACTIONS                                                                                   #
####################################################################################################







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