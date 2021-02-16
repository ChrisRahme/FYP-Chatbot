# Versions

## Future

* Continuous Deployment via GitHub Actions (<https://forum.rasa.com/t/github-custom-action-failure-unexpected-token-conditional-binary-operator-expected/40260/2>).
  * Includes training and testing + uploading model & building Action Server image + upgrading Rasa X deployment.
  * Takes about 40 minutes to complete. Check progress in <https://github.com/ChrisRahme/fyp-chatbot/actions>.

## Current

* Upgraded for Rasa 2.3.0
  * DIET and TED confidence use now cosine distance.
  * DIET loss type is now cross_entropy (softmax is deprecated) and constrain_similarities is set to True (recommended when using cross_entropy)
* Pipeline upgrades
  * See Rasa 2.3.0 modifications mentioned above.
  * The pipeline was changed to use SpaCy. The chatbot does a way better job at detecting city names.
  * Number of epochs was overkill, and maybe still is. It went from 16k to 1k epochs for DIET.
* Actions & training data
  * Weather action now supports inputs without a city name and will use last city name in that case.
  * A new Out-Of-Scope intent was added with a corresponding custom action that does a Google search.
* Other
  * "lookup" entry in _nlu.yml_ is removed, added _data/lookups/pokemon_name.yml_ instead to let Rasa search automatically.

## 2021.02.13

* This chatbot can recognize if a given Pokemon exists and gives you the weather in a given city or country.
* Continuous Integration support, Non-Countinuous Deployment via docker push/pull.
