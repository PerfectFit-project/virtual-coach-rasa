This is a simple conversational agent implemented in Rasa 2.0.2.

## How to Run

WORK IN PROGRESS

These instructions do not allow the custom actions to be executed:
- Type `docker run -it -v $(pwd):/app rasa/rasa:2.0.2-full shell` within the "Rasa_Bot"-folder.
   - On Windows, replace `$(pwd)` with `%cd%`.
- Then you can communicate with the agent. Note that custom actions taken by the agent fail.
- See here for the instructions: https://rasa.com/docs/rasa/docker/building-in-docker/.

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