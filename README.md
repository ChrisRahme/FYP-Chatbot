[![CodeFactor](https://www.codefactor.io/repository/github/chrisrahme/fyp-chatbot/badge?s=1b03c9b6a6d6173575258376b2664506a5564f0c)](https://www.codefactor.io/repository/github/chrisrahme/fyp-chatbot)

[Chatbot](https://github.com/ChrisRahme/fyp-chatbot) | [Web Widget](https://github.com/ChrisRahme/fyp-webapp) | [Mobile App](https://github.com/ChrisRahme/fyp-mobapp)

# Releases

## Current

* Upgraded for [Rasa 2.6.0](https://github.com/RasaHQ/rasa/releases/tag/2.6.0).

## 2021.05.14

* Upgraded for [Rasa 2.5.0](https://github.com/RasaHQ/rasa/releases/tag/2.5.0):
  * Problems:
    * [Rasa 2.4.0](https://github.com/RasaHQ/rasa/releases/tag/2.4.0): `‘charmap’ codec can’t decode` bytes in Arabic and Armenian. Check [rasa topic #41569](https://forum.rasa.com/t/charmap-codec-cant-decode-byte-0x81-after-2-4-0-update/41569?u=chrisrahme), [rasa issue #8215](https://github.com/RasaHQ/rasa/issues/8215), [rasa pull #8286](https://github.com/RasaHQ/rasa/pull/8286).
    * [Rasa 2.4.2](https://github.com/RasaHQ/rasa/releases/tag/2.4.0) fixed above problem but training with `checkpoint_model: True` in the pipeline fails. Check [rasa topic #41706](https://forum.rasa.com/t/checkpoint-model-true-leads-to-keyerror-val-i-acc-after-2-4-2-update/41706?u=chrisrahme) and [rasa issue #8296](https://github.com/RasaHQ/rasa/issues/8296).
  * Supports SpaCy 3.0.
* Pipeline & Policies:
  * Now uses `LanguageModelFeaturizer` in pipeline.
* Actions:
  * Refactored and added helper functions:
    * Added `SlackApp` class to send messages to Slack from custom actions.
    * `DatabaseConnection` constructor can now take optional parameters (either hostname, database, username, password, or a list of them).
    * `get_text_from_lang` can now take a list of lists instead of list of strings to choose a random answer.
  * `ValidateFormTroubleshootInternet` now connects to a database to get the required slots.
  * `ActionRequestHuman` sends message to Slack with username, phone number, Rasa ID, and slot values.
* Intents & training data:
  * Added `request_human` intent which starts `action_request_human`.

## 2021.03.22

* Upgraded for [Rasa 2.3.4](https://github.com/RasaHQ/rasa/releases/tag/2.3.4):
  * DIET,  ResponseSelector, and TED's `model_confidence` went back from `cosine` to `linear_norm` ([rasa issue #8014](https://github.com/rasahq/rasa/issues/8014)).
  * Studying [Rasa 2.4.0](https://github.com/RasaHQ/rasa/releases/tag/2.4.0).
* Pipeline & Policies:
  * See modifications mentioned above.
  * Tensorboard integration.
  * Other minor changes.
* Actions:
  * Refactored and added helper functions:
    * Language helper functions now take a list as argument instead of one parameter per language. This helps easily scale for any number of languages.
    * `get_lang()` and `get_lang_index()` are used in the `get_*_from_lang()` functions to avoid replication of code.
    * Added `reset_slots()` helper function.
    * Prettified output of `announce()`.
  * Override `ActionSessionStart` default action. Now slots are forgotten after a session starts.
  * `ActionAskSlotName`s in `FormValidationAction`s now have a "stop" (🚫) button to stop the form.
* Intents & training data:
  * Added `internet_problem` intent which starts `form_troubleshoot_internet` form.
  * Removed Pokémon features.
* Forms:
  * Added `form_troubleshoot_internet` with its `FormValidationAction` and `ActionAskSlotName`s.
* Multilanguage support:
  * Chatbot now also understands Lebanese texting.

## 2021.03.08

* Actions:
  * Added functions (Modified `Database` class & language-dependent template).
  * Converting utterances into actions that utter the message corresponding to the selected language.
  * Minor code changes.
* Intents & training data:
  * Working on basic customer support.
* Multilanguage support:
  * Converting utterances into actions that utter the message corresponding to the selected language.

## 2021.03.01

* Actions:
  * Added helper classes and functions (Database query & language-dependent utterance)
  * Minor code changes.
* Multilanguage support:
  * Chatbot understands 4 languages: English, French, Arabic, Armenian.
  * Instead of utterances we should use actions that utter the message corresponding to the selected language.
  * The chatbot will reply in a select language independently of the language of the input. The user can change this language at any time.

## 2021.02.24

* Actions & training data:
  * Queries database when asked about quota (using form).
  * Added `how_are_you` intent.
* Other:
  * Added lookup table for person names.

## 2021.02.20

* Upgraded for [Rasa 2.3.0](https://github.com/RasaHQ/rasa/releases/tag/2.3.0):
  * DIET and TED confidence use now cosine distance.
  * DIET loss type is now `cross_entropy` (`softmax` is deprecated) and `constrain_similarities` is set to `True` (recommended when using `cross_entropy`).
* Actions & training data:
  * Weather action now supports inputs without a city name and will use last city name in that case.
  * A new `out_of_scope` intent was added with a corresponding custom action that does a Google search.
* Pipeline:
  * See Rasa 2.3.0 modifications mentioned above.
  * The pipeline was changed to use SpaCy. The chatbot does a way better job at detecting city names.
  * Number of epochs was overkill. It went from 16k to 128 epochs for DIET and TED.
* Other:
  * Added tensorboard support.
  * `lookup` entry in _nlu.yml_ is removed, added _data/lookups/pokemon_name.yml_ instead to let Rasa search automatically.

## 2021.02.13

* This chatbot can recognize if a given Pokemon exists and gives you the weather in a given city or country.
* Continuous Integration support, Non-Countinuous Deployment via docker push/pull.
