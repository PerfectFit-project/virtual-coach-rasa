# Design (v2.0) PerfectFit Virtual Coach system
A sketch of all the system architecture:
<img src = "img/design.png" width = "1000" title="Design">
See it also on [whimsical](https://whimsical.com/perfectfit-UtvRnxdP8P79humXTnjb9J)

## Smartphone applications
### Niceday app (already developed)
The user interacts with the
[NiceDay smartphone app](https://play.google.com/store/apps/details?id=nl.sense.goalie2&hl=nl&gl=US).
This app is developed by [sense-health](https://sense-health.com/) which is part of the consortium.
 
### Sensor data collection app (out of scope)
A separate app for collecting sensor data that is needed to estimate physical capacity. 
* The Niceday app itself cannot gather this data.
* At the start of an activity the sensor data collector is triggered to start recording sensor data.
* After an activity or upon Wifi connection the data is pushed to the PerfectFit sensor data REST API.
* Will be based on an existing app and developed outside of scope of PerfectFit
virtual coach system.
--- 

## Niceday components
### Niceday server (already developed)
* Backend for the Niceday app.
* Data storage: user data, app-interaction data, messages
* Handles authentication

--- 
## PerfectFit virtual coach system components
We cannot change much in the NiceDay app, new PerfectFit features will mostly be implemented 
through the virtual coach that interacts with the user through the messaging function of the 
NiceDay app. 

## Sensor data REST API
A Sensor REST API that allows for the sensor data collection app to send data to PerfectFit system

## Rasa agent
The conversational agent developed in the [Rasa](https://rasa.com/) framework.
* Given an input message of the user, perform the appropriate action.
* Actions can range from a simple text message response to something more complex, such as:
  - calling an algorithm 
  - querying the perfectfit database
  - calling the niceday-api for information from niceday-server

## Rasa agent REST API
Allows for other components to interact with the agent.

## niceday-broker
Sends back and forth messages from a niceday user between the Niceday server and the rasa agent.

## niceday-api
The ‘niceday-api’ that allows control over certain functionalities in the niceday app.
It is a node.js REST API that wraps functions that we need from the javascript Niceday client 
[goalie-js](https://github.com/senseobservationsystems/goalie-js).
* Request data from the niceday server
* Read from and manage custom trackers 
(an example custom tracker: a simple panel for logging the number of cigarettes smoked)
* Interact with Niceday app calendar.

## PostgreSQL database
Stores PerfectFit-specific data, 
* Stores:
  - Data about the user (name, age, stage of patient journey, preferences)
  - Sensor data.
  - Any data that we need to conduct research
* The interface to it will be an SqlAlchemy ORM (so no API abstraction)

## Content Management System
Interface for domain experts to control the content of the application 
(I.e. what the conversational agent responds with).
We still have to decide how much content/behavior we want to be managed vs to be hard-coded.
Some options:
1. [Rasa X](https://rasa.com/docs/rasa-x/), a (proprietary) tool for Conversation-Driven Development (CDD), 
the process of listening to your users and using those insights to improve your AI assistent.
This provides (amongst others) a UI for annotation of conversations, thereby steering the
behavior of the agent.
2. Rasa agent behavior and training data is fully controlled by developers, but some specific content comes from a CMS. 
The CMS is basically a mapping from a response identifier (i.e. UTTER_WELCOME) to the actual 
response (i.e. 'Welcome to this app')

## Algorithm components
A number of algorithm components 
* For example: a Sensor Data Processor, that has as input sensor data for an activity, 
and outputs some useful information about the activity (i.e. was the capacity threshold reached).
* Are Python libraries that are imported and used by Rasa agent

## Admin UI
Interface to inspect data, monitor the system, and perform actions in the system.
* How this will look like will emerge based on problems we encounter
