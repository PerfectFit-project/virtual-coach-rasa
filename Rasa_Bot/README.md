This is a simple conversational agent implemented in Rasa 2.0.2.

## How to Run

See here for the instructions from Rasa: https://rasa.com/docs/rasa/docker/deploying-in-docker-compose/.

The steps are as follows:
- Make sure that you have Docker installed.
- Navigate to the "Rasa_Bot"-folder on your laptop.
- Type `docker-compose up`.
- Now you can communicate with the both via its REST API. E.g. on Windows, type `curl http://localhost:5005/webhooks/rest/webhook -d "{\"message\": \"Could you please send me the planning for next week?\", \"sender\":\"user\"}"`. Note that the escaping of the double-quotes is a fix that is needed on Windows.

## Conversation Paths
The agent is built for a very simple conversation, as shown in the image below.

<img src = "Readme_Images/Dialog_Flow.PNG" width = "800" title="Dialog Flow">

## Components

- actions
   - actions.py: custom actions, e.g. for reading from a database or file.
- data:
   - nlu.yml: contains the intents that the agent can recognize and training examples for each such intent.
   - rules.yml: *default file, not used at the moment.*
   - stories.yml: training stories, i.e. the conversation paths the agent can take.
- models: contains trained models
- domain.yml: contains all slots, utterances, etc.