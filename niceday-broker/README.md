# Niceday Broker

## Overview
This application listens to incoming messages from the Niceday server.
When a message comes in from a user sent to the therapist account, 
the message is forwarded to the rasa agent rest API. 
The rasa response is then sent back to the user in the Niceday app. 

### Setup
1. Install npm and node-js, following [these instructions](https://www.npmjs.com/get-npm).
2. Install dependencies: Run `npm install`.
3. Create a file called `.env` in this folder
Set THERAPIST_EMAIL_ADDRESS and THERAPIST_PASSWORD in your `.env` file, see .env-example. 
These will be loaded as environment variables and will thus be available in the app.
You will get a `InvalidUsernamePasswordError` if the username or password is invalid.


### Running the server
To run the server, run:
```
npm start
```

### Running the full Niceday conversational agent application
You'll need to run both this niceday-broker and the Rasa_Bot 
(see [Readme of Rasa_Bot](https://github.com/PerfectFit-project/virtual-coach-server/blob/main/Rasa_Bot/README.md)) 
to have a working conversational agent in the Niceday app.