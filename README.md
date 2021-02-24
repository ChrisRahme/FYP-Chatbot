# Versions

## Future

* Continuous Deployment via GitHub Actions (<https://forum.rasa.com/t/github-custom-action-failure-unexpected-token-conditional-binary-operator-expected/40260/2>).
  * Includes training and testing + uploading model & building Action Server image + upgrading Rasa X deployment.

## Current

* Multilanguage support
  * Working on it

## 2021.02.24

* Actions & training data
  * Queries database when asked about quota (using form)
  * Added "How are you?" intent
* Other
  * Added lookup table for person names

## 2021.02.20

* Upgraded for Rasa 2.3.0
  * DIET and TED confidence use now cosine distance.
  * DIET loss type is now cross_entropy (softmax is deprecated) and constrain_similarities is set to True (recommended when using cross_entropy).
* Actions & training data
  * Weather action now supports inputs without a city name and will use last city name in that case.
  * A new Out-Of-Scope intent was added with a corresponding custom action that does a Google search.
* Pipeline
  * See Rasa 2.3.0 modifications mentioned above.
  * The pipeline was changed to use SpaCy. The chatbot does a way better job at detecting city names.
  * Number of epochs was overkill. It went from 16k to 128 epochs for DIET and TED.
* Other
  * Added tensorboard support.
  * "lookup" entry in _nlu.yml_ is removed, added _data/lookups/pokemon_name.yml_ instead to let Rasa search automatically.

## 2021.02.13

* This chatbot can recognize if a given Pokemon exists and gives you the weather in a given city or country.
* Continuous Integration support, Non-Countinuous Deployment via docker push/pull.
