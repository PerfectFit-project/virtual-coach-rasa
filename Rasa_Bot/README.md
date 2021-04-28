This is a simple conversational agent implemented in Rasa 2.0.2.

## How to Run

See here for the instructions from Rasa: https://rasa.com/docs/rasa/docker/deploying-in-docker-compose/.

The steps are as follows:
- Make sure that you have Docker and Docker Compose installed. You can check whether you do by typing `docker -v && docker-compose -v`.
- Navigate to the "Rasa_Bot"-folder on your laptop.
- Type `docker-compose up`.
- Now you can communicate with the bot via its REST API. E.g. on Windows, type `curl http://localhost:5005/webhooks/rest/webhook -d "{\"message\": \"Could you please send me the planning for next week?\", \"sender\":\"user\"}"`. Note that the escaping of the double-quotes is a fix that is needed on Windows.
   - The output should be something like this: [{"recipient_id":"user","text":"Hey Kees!"},{recipient_id":"user","text":"Sure, you should ...
   - See [this page](https://rasa.com/docs/rasa/connectors/your-own-website#restinput) for details on how to use the REST channel.
   
## Conversation Flow
The agent is built for a very simple conversation, as shown in the image below.

<img src = "Readme_Images/Dialog_Flow.PNG" width = "800" title="Dialog Flow">

## Components

- actions
   - actions.py: custom actions, e.g. for reading from a database or file.
- data:
   - nlu.yml: contains the intents that the agent can recognize and training examples for each such intent. Currently there is a total of 3 intents, one for confirming, one for denying, and one for requesting the weekly planning.
   - rules.yml: *default file, not used at the moment.*
   - stories.yml: training stories, i.e. the conversation paths the agent can take.
- models: contains trained models
- domain.yml: contains all slots, utterances, etc.
