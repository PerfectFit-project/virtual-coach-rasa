This is a simple conversational agent implemented in Rasa 2.0.2.

## Conversation Paths
The agent is built for a very simple conversation, as shown in the image below.

<img src = "Readme_Images/Dialog_Flow.PNG" width = "400" title="Dialog Flow">

## Components

- actions
   - actions.py: custom actions, e.g. for reading from a database or file.
- data:
   - nlu.yml: contains the intents that the agent can recognize and training examples for each such intent.
   - rules.yml: *default file, not used at the moment.*
   - stories.yml: training stories, i.e. the conversation paths the agent can take.
- models: contains trained models
- domain.yml: contains all slots, utterances, etc.