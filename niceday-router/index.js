'use strict';

var goalieJs = require('@sense-os/goalie-js')
var Chat = goalieJs.Chat
var SenseServerEnvironment = goalieJs.SenseServerEnvironment
var ConnectionStatus = goalieJs.ConnectionStatus

//Read in environment variables from .env file
require('dotenv').config()
const THERAPIST_USER_ID = parseInt(process.env.THERAPIST_USER_ID)
const TOKEN = process.env.NICEDAY_TOKEN

function getRasaResponse(text) {
  return 'you said: ' + text;
}

function handleIncomingMessage(message) {
  console.log(message);
  if (message.from !== THERAPIST_USER_ID) {
    var rasaResponse = getRasaResponse(message.content.TEXT)
    chatSdk.sendTextMessage(message.from, rasaResponse).then(response => {
      console.log("Successfully sent the message", response)});
  }
};

// Setup connection
const chatSdk = new Chat();
chatSdk.init(SenseServerEnvironment.Alpha);
chatSdk.connect(THERAPIST_USER_ID, TOKEN)

// Send initial presence when connected
chatSdk.subscribeToConnectionStatusChanges((connectionStatus) => {
 if (connectionStatus === ConnectionStatus.Connected) {
    chatSdk.sendInitialPresence();
 }
});
console.log('Listening to incoming message...')
chatSdk.subscribeToIncomingMessage(handleIncomingMessage);
