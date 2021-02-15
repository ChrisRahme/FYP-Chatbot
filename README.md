## Current
* The pipeline was changed to use SpaCy. The chatbot does a way better job at detecting city names.
* Number of epochs was overkill, and maybe still is. It went from 16k to 1k epochs for DIET.
* A new Out-Of-Scope intent was added with a corresponding custom action that does a Google search.

## 2021.02.13
* This chatbot can recognize if a given Pokemon exists and gives you the weather in a given city or country.