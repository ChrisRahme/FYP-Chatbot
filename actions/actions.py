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
from rasa_sdk.events import ActionReverted, AllSlotsReset, SlotSet, FollowupAction, ReminderCancelled, ReminderScheduled, SessionStarted, UserUtteranceReverted
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



def announce(action, tracker = None):
    output = '='*100 + '\n>>> Action: ' + action.name()
    if tracker:
        output += '\n\n' + str(tracker.latest_message)
    print(output)



def get_text_from_lang(tracker, utter_en = '', utter_fr = None, utter_ar = None, utter_hy = None):
    current_language = 'English'
    utterance = utter_en

    if not utter_fr:
        utter_fr = utterance
    if not utter_ar:
        utter_ar = utterance
    if not utter_hy:
        utter_hy = utterance

    try:
        current_language = tracker.slots['language'].title()
        if current_language == 'French':
            utterance = utter_fr
        elif current_language == 'Arabic':
            utterance = utter_ar
        elif current_language == 'Armenian':
            utterance = utter_hy
    except Exception as e:
        print(f'\n> get_text_from_lang: [ERROR] {e}')

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
        print(f'\n> get_template_from_lang: {template}')
    except Exception as e:
        print(f'\n> get_template_from_lang: [ERROR] {e}')

    return template



def get_buttons_from_lang(tracker, titles_en, titles_fr, titles_ar, titles_hy, payloads):
    current_language = 'English'
    length  = len(payloads)
    buttons = []

    try:
        current_language = tracker.slots['language'].title()
        if current_language == 'French':
            for i in range(length):
                buttons.append({'title': titles_fr[i], 'payload': payloads[i]})
        elif current_language == 'Arabic':
            for i in range(length):
                buttons.append({'title': titles_ar[i], 'payload': payloads[i]})
        elif current_language == 'Armenian':
            for i in range(length):
                buttons.append({'title': titles_hy[i], 'payload': payloads[i]})
        else:
            for i in range(length):
                buttons.append({'title': titles_en[i], 'payload': payloads[i]})
        print(f'\n> get_buttons_from_lang: {buttons}')
    except Exception as e:
        print(f'\n> get_buttons_from_lang: [ERROR] {e}')

    return buttons



####################################################################################################
# SLOTS                                                                                            #
####################################################################################################



class ActionAskUsername(Action):
    def name(self):
        return 'action_ask_username'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        utterance = get_text_from_lang(
            tracker,
            'Please enter your Username, L Number, or Phone Number.',
            'S\'il vous plaît entrez votre Nom d\'Utilisateur, L Number, ou Numéro de Téléphone.',
            '.(Username أو L Number أو Phone Number) الرجاء إدخال اسم المستخدم',
            'Խնդրում ենք մուտքագրել ձեր օգտվողի անունը: (Username, L Number, կամ Phone Number).'
        )
        print('\nBOT:', utterance)
        dispatcher.utter_message(utterance)
        return []



class ActionAskPassword(Action):
    def name(self):
        return 'action_ask_password'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        utterance = get_text_from_lang(
            tracker,
            'Please enter your password.',
            'S\'il vous plaît entrez votre mot de passe.',
            '.(password) من فضلك أدخل رقمك السري',
            'Խնդրում ենք մուտքագրել ձեր գաղտնաբառը (username).'
        )
        print('\nBOT:', utterance)
        dispatcher.utter_message(utterance)
        return []



####################################################################################################
# FORM VALIDATION ACTIONS                                                                          #
####################################################################################################



class ValidateFormLogIn(FormValidationAction):
    def name(self):
        return 'validate_form_log_in'

    
    # Custom Slot Mappings: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        required_slots = predefined_slots
        return required_slots

    '''
    # Validating Form Input: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def validate_username(self, value, dispatcher, tracker, domain):
        if not tracker.get_slot('loggedin'):
            username   = value.lower()
            login_type = 'username'
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

            db.disconnect()

            if count == 1:
                print('\n> validate_username:', username, login_type)
                return {'username': username, 'loggedin': False, 'login_type': login_type}

            elif count == 0:
                utterance = get_text_from_lang(
                    tracker,
                    'Sorry, {} is not a registered Username, L Number, of Phone Number.'.format(username),
                    'Désolé, {} n\'est pas un Utilisateur, L Number, ou Numéro de Téléphone enregistré.'.format(username),
                    'عذرًا، {} ليس مستخدمًا مسجلاً'.format(username),
                    'Ներողություն, {} - ը գրանցված օգտվող չէ:'.format(username)
                )
                print('\nBOT:', utterance)
                dispatcher.utter_message(utterance)
                return {'username': None, 'loggedin': False, 'login_type': None}

            else:
                login_type = login_type.replace('_', ' ')
                utterance = f'There seems to be {count} users with the {login_type} {username}. Please report this error.'
                print('\nBOT:', utterance)
                dispatcher.utter_message(utterance)
                return {'username': None, 'loggedin': False, 'login_type': None}
        
        else: # Already logged in
            utterance = get_text_from_lang(
                tracker,
                'You are already logged in. If you want to log out, please say "log out".',
                'Vous êtes déjà connecté. Si vous souhaitez vous déconnecter, veuillez dire «déconnexion» ou «log out».',
                'لقد قمت بتسجيل الدخول بالفعل. إذا كنت تريد الخروج ، من فضلك قل "تسجيل الخروج" أو "log out".',
                'Դուք արդեն մուտք եք գործել համակարգ: Եթե ցանկանում եք դուրս գալ, խնդրում ենք ասել «դուրս գալ» կամ «log out»:'
            )
            print('\nBOT:', utterance)
            dispatcher.utter_message(utterance)
            return {'password': 'secret', 'loggedin': True}


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
                print('\n> validate_password:', username, password)
                return {'password': 'secret', 'loggedin': True}

            else:
                utterance = get_text_from_lang(
                    tracker,
                    'Sorry, you entered an incorrect password for {}.'.format(username),
                    'Désolé, vous avez entré un mot de passe incorrect pour {}.'.format(username),
                    'عذرًا ، لقد أدخلت كلمة مرور غير صحيحة لـ {}'.format(username),
                    'Ներողություն, դուք սխալ գաղտնաբառ եք մուտքագրել {} - ի համար:'.format(username)
                )
                print('\nBOT:', utterance)
                dispatcher.utter_message(utterance)
                return {'password': None, 'loggedin': False}

        else: # Already logged in
            username = tracker.get_slot('username')
            utterance = get_text_from_lang(
                    tracker,
                    'You are logged in as {}.'.format(username),
                    'Vous êtes connecté en tant que {}'.format(username),
                    'أنت مسجل دخولك باسم {}.'.format(username),
                    'Դուք մուտք եք գործել որպես {}:'.format(username)
                )
            print('\nBOT:', utterance)
            dispatcher.utter_message(utterance)
            return {'username': username, 'password': 'secret', 'loggedin': True}
    '''


class ValidateFormTroubleshootInternet(FormValidationAction):
    def name(self):
        return 'validate_form_troubleshoot_internet'

    
    # Custom Slot Mappings: https://rasa.com/docs/rasa/forms/#custom-slot-mappings
    async def required_slots(self, predefined_slots, dispatcher, tracker, domain):
        required_slots = [predefined_slots[1], predefined_slots[0]] # To ask for username before password
        return required_slots



####################################################################################################
# FORM ACTIONS                                                                                     #
####################################################################################################



####################################################################################################
# TEMPLATE UTTERANCES                                                                              #
####################################################################################################



class ActionUtterGreet(Action):
    def name(self):
        return 'action_utter_greet'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        template = get_template_from_lang(tracker, 'utter_greet')
        buttons  = get_buttons_from_lang(
            tracker,
            ['Wireless', 'Internet', 'DSL Internet', 'CableVision TV'],
            ['Sans Fil', 'Internet', 'Internet DSL', 'CableVision TV'],
            ['لاسلكي','إنترنت','DSL إنترنت','تلفزيون الكابل'],
            ['Անլար', 'Ինտերնետ', 'DSL ինտերնետ', 'CableVision TV'],
            [
                '/inform_service_type{"service_type": "wireless"}',
                '/inform_service_type{"service_type": "internet"}',
                '/inform_service_type{"service_type": "dsl"}',
                '/inform_service_type{"service_type": "cablevision"}'
            ]
        )
        print('\nBOT: {utter_greet}')
        dispatcher.utter_message(template = template, buttons = buttons)
        return []



class ActionUtterGoodbye(Action):
    def name(self):
        return 'action_utter_goodbye'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        dispatcher.utter_message(template = get_template_from_lang(tracker, 'utter_goodbye'))
        return []
            


class ActionUtterYoureWelcome(Action):
    def name(self):
        return 'action_utter_youre_welcome'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        dispatcher.utter_message(template = get_template_from_lang(tracker, 'utter_youre_welcome'))
        return []



####################################################################################################
# TEXT UTTERANCES                                                                                  #
####################################################################################################



class ActionUtterChangeLanguage(Action):
    def name(self):
        return 'action_utter_change_language'
    

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)

        buttons = [ # https://forum.rasa.com/t/slots-set-by-clicking-buttons/27629
            {'title': 'English',  'payload': '/set_language{"language": "English"}'},
            {'title': 'Français', 'payload': '/set_language{"language": "French"}'},
            {'title': 'عربي',     'payload': '/set_language{"language": "Arabic"}'},
            {'title': 'հայերեն',  'payload': '/set_language{"language": "Armenian"}'}
        ]
        
        text = get_text_from_lang(
            tracker,
            'Choose a language:',
            'Choisissez une langue:',
            ':اختر لغة',
            'Ընտրեք լեզու ՝'
        )            
        
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

        utterance = get_text_from_lang(
            tracker,
            'If you need help recovering your IDM ID or your password, click on the link below:',
            'Si vous avez besoin d\'aide pour récupérer votre ID IDM ou votre mot de passe, cliquez sur le lien ci-dessous:',
            'لا مشكلة. إذا كنت بحاجة إلى مساعدة في استعادة معرّف IDM أو كلمة مرورك ، فانقر على الرابط أدناه:',
            'Ոչ մի խնդիր. Եթե ձեր IDM ID- ն կամ գաղտնաբառն վերականգնելու համար օգնության կարիք ունեք, կտտացրեք ստորև նշված հղմանը.'
        )
        text = utterance + '\n' + url
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return []



class ActionLoggedIn(Action):
    def name(self):
        return 'action_logged_in'


    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        if tracker.get_slot('loggedin'):
            username = tracker.get_slot('username')
            login_type = tracker.get_slot('login_type').replace('_', ' ')

            utterance = get_text_from_lang(
                tracker,
                'You are logged in with {} being {}'.format(login_type, username),
                'Vous êtes connecté avec {} étant {}'.format(login_type, username),
                'لقد قمت بتسجيل الدخول {} يجري {}'.format(login_type, username),
                'Դուք մուտք եք գործել ՝{} լինելով {}'.format(login_type, username)
            )            
            print('\nBOT:', utterance)
            dispatcher.utter_message(utterance)

        return []
#
#        else:
#            return [SlotSet('username', None), SlotSet('password', None)]



class ActionUtterAccountTypes(Action):
    def name(self):
        return 'action_utter_account_types'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            'Which account type are you asking about?',
            'Quel type de compte avez-vous?',
            'ما نوع الحساب الذي تسأل عنه؟',
            'Հաշվի ո՞ր տեսակի մասին եք հարցնում:'
        )
        buttons  = get_buttons_from_lang(
            tracker,
            ['Consumer / Residential', 'Small Business', 'Bank'],
            ['Consommateur / Résidentiel', 'Petite Entreprise', 'Banque'],
            ['استهلاكي / سكني', 'أعمال صغيرة', 'مصرف'],
            ['Սպառող / բնակելի', 'Փոքր բիզնես', 'Բանկ'],
            [
                '/inform_account_type{"account_type": "consumer"}',
                '/inform_account_type{"account_type": "business"}',
                '/inform_account_type{"account_type": "bank"}'
            ]
        )
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons)
        return []



class ActionUtterTopicTypes(Action):
    def name(self):
        return 'action_utter_topic_types'
    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)
        text = get_text_from_lang(
            tracker,
            'Choose a topic to chat about:',
            'Choisissez un sujet de discussion:',
            'اختر موضوعًا للمناقشة:',
            'Ընտրեք քննարկման թեմա:'
        )
        buttons  = get_buttons_from_lang(
            tracker,
            ['Billing, Plans & Equipment Setup', 'Payments', 'Shopping', 'Order Status', 'Moving or Changing Service', 'Troubleshooting & Repairs', 'Online Account & Sign-in Help'],
            ['Facturation, Plans et Configuration de l\'Équipement', 'Paiements', 'Achats', 'Statut de Commande', 'Déménagement ou Changement de Service', 'Dépannage et Réparations', 'Compte en Ligne et Aide à la Connexion'],
            ['إعداد الفواتير والخطط والمعدات', 'المدفوعات', 'التسوق', 'حالة الطلب', 'نقل أو تغيير الخدمة', 'استكشاف الأخطاء وإصلاحها والإصلاحات', 'حساب عبر الإنترنت وتعليمات تسجيل الدخول'],
            ['Վճարների, պլանների և սարքավորումների տեղադրում', 'Վճարներ', 'Գնումներ', 'Պատվերի կարգավիճակ', 'Շարժվող կամ փոխելու ծառայություն', 'Խնդիրների լուծում և վերանորոգում', 'Առցանց հաշվի և մուտքի օգնություն'],
            [
                '/inform_topic_type{"topic_type": "billing"}',
                '/inform_topic_type{"topic_type": "payments"}',
                '/inform_topic_type{"topic_type": "shopping"}',
                '/inform_topic_type{"topic_type": "order"}',
                '/inform_topic_type{"topic_type": "changing"}',
                '/inform_topic_type{"topic_type": "troubleshooting"}',
                '/inform_topic_type{"topic_type": "account"}'
            ]
        )
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = buttons)
        return []



class ActionUtterTopicSamples(Action):
    def name(self):
        return 'action_utter_topic_samples'


    def get_sample_questions(self, topic_type, account_type, service_type):
        examples_en = [
            'sample question 1',
            'sample question 2',
            'sample question 3'
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
            f'\nYou can say things like:'
            f'\n- {examples_en}'
        )
        text_fr = (
            'Vous avez choisi:'
             f'\n- Type de service: {service_type}'
             f'\n- Type de compte: {account_type}'
             f'\n- Topic: {topic_type}'
            f'\nVous pouvez demander:'
            f'\n- {examples_fr}'
        )
        text_ar = (
            'اخترت:'
            f'\n- نوع الخدمة: {service_type}'
            f'\n- نوع الحساب: {account_type}'
            f'\n- الموضوع: {topic_type}'
            f'\nتستطيع أن تسأل:'
            f'\n- {examples_ar}'
        )
        text_hy = (
            'Դուք ընտրեցիք:'
            f'\n- ծառայության տեսակը: {service_type}'
            f'\n- Հաշվի տեսակը: {account_type}'
            f'\n- Թեմա: {topic_type}'
            f'\nԴու կարող ես հարցնել:'
            f'\n- {examples_hy}'
        )

        utterance = get_text_from_lang(tracker, text_en, text_fr, text_ar, text_hy)            
        print('\nBOT:', utterance)
        dispatcher.utter_message(utterance)

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
            current_language == 'English'
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

        if tracker.get_slot('loggedin') == True:
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
                print(f'\n> ActionFetchQuota: [ERROR1] {e}')
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
                        'You spent {} GB of your unlimited quota this month.'.format(consumption),
                        'Vous avez dépensé {} Go de votre quota illimité pour ce mois.'.format(consumption),
                        '.لقد أنفقت {} غيغابايت من حصتك غير المحدودة هذا الشهر'.format(consumption),
                        'Դուք անցկացրել {} ԳԲ ձեր անսահման քվոտայի այս ամսվա.'.format(consumption)
                    )
                    print('\nBOT:', utterance)
                    dispatcher.utter_message(utterance)
                else:
                    ratio = consumption*100/quota
                    utterance = get_text_from_lang(
                        tracker,
                        'You spent {} GB ({}%) of your {} GB quota for this month.'.format(consumption, ratio, quota),
                        'Vous avez dépensé {} Go ({}%) de votre quota de {} Go pour ce mois.'.format(consumption, ratio, quota),
                        '.لقد أنفقت {} غيغابايت ({}٪) من حصتك البالغة {} غيغابايت لهذا الشهر'.format(consumption, ratio, quota),
                        'Այս ամսվա համար ծախսեցիք ձեր {} ԳԲ քվոտայի {} ԳԲ ({}%).'.format(consumption, ratio, quota)
                    )
                    print('\nBOT:', utterance)
                    dispatcher.utter_message(utterance)

            except Exception as e:
                print(f'\n> ActionFetchQuota: [ERROR2] {e}')
                dispatcher.utter_message('Sorry, there was an error.')

            return []
        
        else: # Not logged in
            utterance = get_text_from_lang(
                tracker,
                'You are not logged in. Please type "log in" to log in.',
                'Vous n\'êtes pas connecté. Veuillez ecrire «connexion» ou «log in» pour vous connecter.',
                'أنت لم تسجل الدخول. من فضلك قل "تسجيل الدخول" لتسجيل الدخول.',
                'Դուք մուտք չեք գործել: Մուտք գործելու համար խնդրում ենք ասել «մուտք գործել»:'
            )
            print('\nBOT:', utterance)
            dispatcher.utter_message(utterance)

    
    '''
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
                utterance = get_text_from_lang(
                    tracker,
                    'You spent {} GB of your unlimited quota this month.'.format(consumption),
                    'Vous avez dépensé {} Go de votre quota illimité pour ce mois.'.format(consumption),
                    '.لقد أنفقت {} غيغابايت من حصتك غير المحدودة هذا الشهر'.format(consumption),
                    'Դուք անցկացրել {} ԳԲ ձեր անսահման քվոտայի այս ամսվա.'.format(consumption)
                )
                dispatcher.utter_message(utterance)
            else:
                ratio = consumption*100/quota
                utterance = get_text_from_lang(
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
    '''



class ActionCheckExistence(Action):
    knowledge = Path('data/lookups/pokemon_name.txt').read_text().split('\n')

    def name(self) -> Text:
        return 'action_check_existence'

    def run(self, dispatcher, tracker, domain):
        announce(self, tracker)

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