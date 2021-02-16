# Versions

## Future

* Continuous Deployment via GitHub Actions (<https://forum.rasa.com/t/github-custom-action-failure-unexpected-token-conditional-binary-operator-expected/40260/2>).
  * Includes training and testing + uploading model & building Action Server image + upgrading Rasa X deployment.
  * Takes about 40 minutes to complete. Check progress in <https://github.com/ChrisRahme/fyp-chatbot/actions>.

## Current

* The pipeline was changed to use SpaCy. The chatbot does a way better job at detecting city names.
* Number of epochs was overkill, and maybe still is. It went from 16k to 1k epochs for DIET.
* A new Out-Of-Scope intent was added with a corresponding custom action that does a Google search.

## 2021.02.13

* This chatbot can recognize if a given Pokemon exists and gives you the weather in a given city or country.
* Continuous Integration support, Non-Countinuous Deployment via docker push/pull.
