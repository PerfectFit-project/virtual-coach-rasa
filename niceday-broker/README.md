# Niceday Broker

## Overview
This application listens to incoming messages from the Niceday server.
When a message comes in from a user sent to the therapist account, 
the message is forwarded to the rasa agent rest API. 
The rasa response is then sent back to the user in the Niceday app. 

### Setup
1. Install npm and node-js, following [these instructions](https://www.npmjs.com/get-npm).
2. Install dependencies: Run `npm install`.
3. Run `node login.mjs emailaddress password`, 
where emailaddress and password should be the credentials for the therapist account. 
This will print the user id of the therapist as well as the token that you need to authenticate.
4. Create a file called `.env` in the root of this app.
Save the therapist user id and token in your `.env` file as THERAPIST_USER_ID and NICEDAY_TOKEN respectively,
see .env-example. These will be loaded as environment variables and will thus be available in the app.

### Running the server
To run the server, run:
```
npm start
```

### Running the full Niceday conversational agent application
You'll need to run both this niceday-router and the Rasa_Bot 
(see Readme in Rasa_Bot) to have a working conversational agent in the
Niceday app.