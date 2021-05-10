This is a simple conversational agent implemented in Rasa 2.0.2.

All conversations are stored in memory, which means that they are lost once the Rasa server is restarted. It is possible to set up a tracker store so that the conversations persist. See [this page](https://rasa.com/docs/rasa/tracker-stores) for more information.

## How to Run

See here for the instructions from Rasa: https://rasa.com/docs/rasa/docker/deploying-in-docker-compose/.

The steps are as follows:
- Make sure that you have Docker and Docker Compose installed. You can check whether you do by typing `docker -v && docker-compose -v`.
- Navigate to the "Rasa_Bot"-folder on your laptop.
- Type `docker-compose up`.
- Now you can communicate with the bot via its REST API. E.g. on Windows, type `curl http://localhost:5005/webhooks/rest/webhook -d "{\"message\": \"Kan ik de agenda voor de week krijgen?\", \"sender\":\"user\"}"`. Note that the escaping of the double-quotes is a fix that is needed on Windows.
   - The output for the above command should be something like this: [{"recipient_id":"user","text":"Hoi Kees!"},{"recipient_id":"user","text":"Sure, you should ...
   - See [this page](https://rasa.com/docs/rasa/connectors/your-own-website#restinput) for details on how to use the REST channel.
   
## Conversation Flow
The agent is built for very simple conversations. It's capabilities are twofold. First, it will always respond according to the rules shown below. For example, it will always respond with a goodbye-message if the user sends a goodbye-message.

<img src = "Readme_Images/Dialog_Rules.PNG" width = "500" title="Dialog Rules">

Secondly, the agent is trained for three simple conversations. One is about the weekly planning, one is about the agent's mood, as asked about by the user, and one is about a greeting, initiated by the user.

<img src = "Readme_Images/Dialog_Flow.PNG" width = "500" title="Dialog on weekly plan, iniated by the user.">

<img src = "Readme_Images/Dialog_Flow_Hi.PNG" width = "500" title="Dialog based on greeting by user.">

<img src = "Readme_Images/Dialog_Flow_Mood_User_Initiated.PNG" width = "600" title="Dialog on mood, initiated by the user.">

The timeout is currently set to 5 minutes (in the "domain.yml"-file). This is the period of time after which the agent assumes that the current conversation is over. Sending a message from the user after this timeout period has passed then starts a new conversation. A new conversation can also explicitly be started by sending the message "/restart".

## Components

- actions
   - actions.py: custom actions, e.g. for reading from a database or file.
- data:
   - nlu.yml: contains the intents that the agent can recognize and training examples for each such intent. Currently there is a total of 3 intents, one for confirming, one for denying, and one for requesting the weekly planning.
   - rules.yml: *default file, not used at the moment.*
   - stories.yml: training stories, i.e. the conversation paths the agent can take.
- models: contains trained models
- domain.yml: contains all slots, utterances, etc.
