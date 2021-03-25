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

class ActionAskUsername(Action):
    def name(self):
        return 'action_ask_username'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please enter your Username, L Number, or Phone Number, or press "🚫" to stop.',
            'Veuillez entrer votre nom d\'utilisateur, L Number, ou Numéro de Téléphone, ou appuyez sur "🚫" pour arrêter.',
            'الرجاء إدخال اسم المستخدم أو رقم L أو رقم الهاتف ، أو اضغط على "🚫" للإيقاف.',
            'Կանգնեցնելու համար խնդրում ենք մուտքագրել ձեր օգտանունը, L համարը կամ հեռախոսահամարը կամ սեղմել «🚫»:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.button_stop_emoji)
        return []



class ActionAskPassword(Action):
    def name(self):
        return 'action_ask_password'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please enter your password.',
            'S\'il vous plaît entrez votre mot de passe.',
            '.(password) من فضلك أدخل رقمك السري',
            'Խնդրում ենք մուտքագրել ձեր գաղտնաբառը (username).'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.button_stop_emoji)
        return []



class ActionAskTiaNoise(Action):
    def name(self):
        return 'action_ask_tia_noise'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Is there noise on the line where the ADSL number is connected?',
            'Y a-t-il du bruit sur la ligne où le numéro ADSL est connecté?',
            'هل توجد ضوضاء على الخط الموصل به رقم ADSL؟',
            'Արդյո՞ք աղմուկ կա այն գծի վրա, որտեղ միացված է ADSL համարը:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []



class ActionAskTiaaNoise(Action):
    def name(self):
        return 'action_ask_tiaa_noise'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please try to contact Ogero on 1515 to resolve the noise on the line.',
            'Veuillez essayer de contacter Ogero au 1515 pour résoudre le bruit sur la ligne.',
            'يرجى محاولة الاتصال بـ Ogero على 1515 لحل الضوضاء على الخط.',
            'Խնդրում ենք փորձել կապվել Ogero- ի հետ 1515-ին `գծի աղմուկը լուծելու համար:'
            ]) + '\n' + _common.get_text_from_lang(
            tracker,
            ['After you resolved the noise issue with Ogero, restart the modem.',
            'Y a-t-il du bruit sur la ligne où le numéro ADSL est connecté?',
            'هل توجد ضوضاء على الخط الموصل به رقم ADSL؟',
            'Արդյո՞ք աղմուկ կա այն գծի վրա, որտեղ միացված է ADSL համարը:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []



class ActionAskTibModemOn(Action):
    def name(self):
        return 'action_ask_tib_modem_on'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please make sure your modem is turned on.',
            'Veuillez vous assurer que votre modem est allumé.',
            'يرجى التأكد من تشغيل المودم الخاص بك.',
            'Համոզվեք, որ ձեր մոդեմը միացված է:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []



class ActionAskTicModemGreen(Action):
    def name(self):
        return 'action_ask_tic_modem_green'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please reboot your modem, wait 30 seconds, and make sure the power LED on your modem is green.',
            'Veuillez redémarrer votre modem, attendez 30 secondes et assurez-vous que la DEL (LED) de votre modem est verte.',
            'يُرجى إعادة تشغيل المودم الخاص بك ، وانتظر 30 ثانية ، وتأكد من أن مصباح الطاقة (LED) الموجود في المودم الخاص بك أخضر.',
            'Վերաբեռնեք ձեր մոդեմը, սպասեք 30 վայրկյան և համոզվեք, որ ձեր մոդեմի էլեկտրական LED- ը կանաչ է:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []



class ActionAskTidNbPhones(Action):
    def name(self):
        return 'action_ask_tid_nb_phones'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['How many faxes and phones do you have?',
            'Combien de fax et de téléphones fixes avez-vous?',
            'كم عدد الفاكسات والهواتف التي لديك؟',
            'Քանի՞ ֆաքս և հեռախոս ունեք:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.button_stop_emoji)
        return []



class ActionAskTieNbSockets(Action):
    def name(self):
        return 'action_ask_tie_nb_sockets'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['How many phone wall sockets do you have?',
            'Combien de prises téléphoniques murales avez-vous?',
            'كم عدد مآخذ توصيل الحائط بالهاتف لديك؟',
            'Քանի՞ հեռախոսի պատի վարդակ ունեք:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.button_stop_emoji)
        return []



class ActionAskTifSplitterInstalled(Action):
    def name(self):
        return 'action_ask_tif_splitter_installed'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please use the following picture to check if your splitter is correctly installed on all your fixed phones and modems.',
            'Veuillez utiliser l\'image suivante pour vérifier si votre répartiteur est correctement installé sur tous vos téléphones fixes et modems.',
            'الرجاء استخدام الصورة التالية للتحقق مما إذا كان جهاز التقسيم مثبتًا بشكل صحيح على جميع الهواتف الثابتة وأجهزة المودم.',
            'Խնդրում ենք օգտագործել հետևյալ նկարը ՝ ստուգելու համար, թե արդյոք ձեր բաժանարարը ճիշտ է տեղադրված ձեր բոլոր ֆիքսված հեռախոսների և մոդեմների վրա:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji, image = 'https://i.imgur.com/aV0uxGx.png')
        return []



class ActionAskTigRjPlugged(Action):
    def name(self):
        return 'action_ask_tig_rj_plugged'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Please make sure the phone cable plugged in the modem is RJ11 and not the Ethernet port.',
            'Veuillez vous assurer que le câble téléphonique branché sur le modem est RJ11 et non le port Ethernet.',
            'يرجى التأكد من أن كبل الهاتف المتصل بالمودم هو RJ11 وليس منفذ Ethernet.',
            'Խնդրում ենք համոզվեք, որ մոդեմի մեջ միացված հեռախոսի մալուխը RJ11 է և ոչ թե Ethernet պորտ:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work)
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji, image = 'https://i.imgur.com/9aUcYs5.png')
        return []



class ActionAskTihOtherPlug(Action):
    def name(self):
        return 'action_ask_tih_other_plug'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Try to plug the modem into another socket.',
            'Essayez de brancher le modem sur une autre prise.',
            'حاول توصيل المودم بمقبس آخر.',
            'Փորձեք մոդեմը միացնել մեկ այլ վարդակի:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work) + ' (' + _common.get_text_from_lang(
                tracker,
                ['Press "no" if you can\'t use another socket.',
                'Appuyez sur "non" si vous ne pouvez pas utiliser une autre prise.',
                'اضغط على "لا" إذا كنت لا تستطيع استخدام مقبس آخر.',
                'Սեղմեք «ոչ» -ը, եթե այլ վարդակից չեք կարող օգտվել:'
            ]) + ')'
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []



class ActionAskTiiOtherModem(Action):
    def name(self):
        return 'action_ask_tii_other_modem'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Try to use another modem.',
            'Essayez d\'utiliser un autre modem.',
            'حاول استخدام مودم آخر.',
            'Փորձեք օգտագործել մեկ այլ մոդեմ:'
            ]) + '\n' + _common.get_text_from_lang(tracker, _common.text_does_it_work) + ' (' + _common.get_text_from_lang(
                tracker,
                ['Press "no" if you can\'t use another modem.',
                'Appuyez sur "non" si vous ne pouvez pas utiliser un autre modem.',
                'اضغط على "لا" إذا كنت لا تستطيع استخدام مودم آخر.',
                'Սեղմեք «ոչ» -ը, եթե այլ մոդեմ չեք կարող օգտագործել:'
            ]) + ')'
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []



class ActionAskTijHasPbx(Action):
    def name(self):
        return 'action_ask_tij_has_pbx'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Do you have a PBX?',
            'Avez-vous un PBX?',
            'هل لديك مقسم؟',
            'Ունե՞ք PBX:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji, image = 'https://techextension.com/images/cloud_pbx_connections.png')
        return []



class ActionAskTikHasLine(Action):
    def name(self):
        return 'action_ask_tik_has_line'

    def run(self, dispatcher, tracker, domain):
        _common.announce(self, tracker)
        text = _common.get_text_from_lang(
            tracker,
            ['Do you have an Internet line?',
            'Avez-vous une ligne Internet?',
            'هل لديك خط انترنت؟',
            'Ինտերնետային գիծ ունե՞ք:'])
        print('\nBOT:', text)
        dispatcher.utter_message(text = text, buttons = _common.buttons_yes_no_stop_emoji)
        return []