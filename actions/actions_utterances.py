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

class ActionUtterAskLanguage(Action):
    def name(self):
        return 'action_utter_ask_language'
    

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        
        text = _common.get_text_from_lang(
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



class ActionUtterSetLanguage(Action):
    def name(self) -> Text:
        return 'action_utter_set_language'
    

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)

        current_language = tracker.slots['language'].title()
        text = 'I only understand English, French, Arabic, and Armenian. The language is now English.'
        
        if current_language == 'English':
            text = 'The language is now English.'
        elif current_language == 'French':
            text = 'La langue est maintenant le Français.'
        elif current_language == 'Arabic':
            text = 'اللغة الآن هي العربية.'
        elif current_language == 'Armenian':
            text = 'Լեզուն այժմ հայերենն է:'
        
        dispatcher.utter_message(text = text)
        
        if not tracker.get_slot('service_type'):
            return [FollowupAction('action_utter_greet')]
        return []



class ActionUtterRecoverCredentials(Action):
    def name(self):
        return 'action_utter_recover_credentials'


    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        url = 'https://myaccount.idm.net.lb/_layouts/15/IDMPortal/ManageUsers/ResetPassword.aspx'
        url = '\n\n' + url

        text = _common.get_text_from_lang(
            tracker,
            ['If you need help recovering your IDM ID or your password, click on the link below:',
            'Si vous avez besoin d\'aide pour récupérer votre ID IDM ou votre mot de passe, cliquez sur le lien ci-dessous:',
            'لا مشكلة. إذا كنت بحاجة إلى مساعدة في استعادة معرّف IDM أو كلمة مرورك ، فانقر على الرابط أدناه:',
            'Ոչ մի խնդիր. Եթե ձեր IDM ID- ն կամ գաղտնաբառն վերականգնելու համար օգնության կարիք ունեք, կտտացրեք ստորև նշված հղմանը.'])
        text = text + '\n' + url
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return []




class ActionUtterGreet(Action):
    def name(self):
        return 'action_utter_greet'
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)

        followup_action = 'action_utter_service_types'

        text = _common.get_text_from_lang(
            tracker,
            ['Hi, I’m GDS automated virtual assistant.',
            'Bonjour, je suis l\'assistant virtuel automatisé de GDS.',
            'مرحبًا ، أنا مساعد افتراضي تلقائي لنظام GDS.',
            'Ողջույն, ես GDS ավտոմատացված վիրտուալ օգնական եմ.'])

        if tracker.get_slot('language') is None or not tracker.get_slot('language'):
            followup_action = 'action_utter_ask_language'
        
        print('\nBOT:', text)
        dispatcher.utter_message(text = text)

        return [FollowupAction(followup_action)]



class ActionUtterServiceTypes(Action):
    def name(self):
        return 'action_utter_service_types'
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            [['How can I help you today?', 'So I can get you to the right place, tell me what service you’d like help with.', 'How can I help?'],
            ['Comment puis-je vous aider?', 'Pour que je puisse vous guider, dites-moi pour quel service vous aimeriez obtenir de l’aide.', 'Comment puis-je aider?'],
            ['حتى أتمكن من إيصالك إلى المكان الصحيح ، أخبرني بالخدمة التي ترغب في المساعدة فيها.', 'كيف يمكنني أن أقدم المساعدة؟'],
            ['Այսպիսով, ես կարող եմ ձեզ ճիշտ տեղ հասցնել, ասեք ինձ, թե որ ծառայության հետ կցանկանայիք օգնել', 'Ինչպե՞ս կարող եմ օգնել:']]
        )
        
        buttons  = _common.get_buttons_from_lang(
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
        
        print('\nBOT:', text, buttons)
        dispatcher.utter_message(text = text, buttons = buttons)

        return []



class ActionUtterAccountTypes(Action):
    def name(self):
        return 'action_utter_account_types'
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Which account type are you asking about?',
            'Quel type de compte avez-vous?',
            'ما نوع الحساب الذي تسأل عنه؟',
            'Հաշվի ո՞ր տեսակի մասին եք հարցնում:'])
        buttons  = _common.get_buttons_from_lang(
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
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Choose a topic to chat about:',
            'Choisissez un sujet de discussion:',
            'اختر موضوعًا للمناقشة:',
            'Ընտրեք քննարկման թեմա:'])
        buttons  = _common.get_buttons_from_lang(
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
        _common.announce(self, tracker)
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

        text = _common.get_text_from_lang(tracker, [text_en, text_fr, text_ar, text_hy])            
        print('\nBOT:', text)
        dispatcher.utter_message(text)

        return []



class ActionUtterLogOut(Action):
    def name(self):
        return 'action_utter_log_out'
    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Okay, loggin you out.'])
        
        print('\nBOT:', text)
        dispatcher.utter_message(text = text)
        return [SlotSet('username', None), SlotSet('password', None), SlotSet('loggedin', False)]
