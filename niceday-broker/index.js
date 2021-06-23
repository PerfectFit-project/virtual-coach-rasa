'use strict';

var goalieJs = require('@sense-os/goalie-js')
var Chat = goalieJs.Chat
var SenseServerEnvironment = goalieJs.SenseServerEnvironment
var ConnectionStatus = goalieJs.ConnectionStatus
var XMLHttpRequest = require("xmlhttprequest").XMLHttpRequest;

//Read in environment variables from .env file
require('dotenv').config()
const THERAPIST_USER_ID = parseInt(process.env.THERAPIST_USER_ID)
const TOKEN = process.env.NICEDAY_TOKEN
const RASA_AGENT_URL = process.env.RASA_AGENT_URL

/**
 * Request a response from rasa for a given text message
 **/
function requestRasa(text, userId, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", RASA_AGENT_URL, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = callback
    var data = JSON.stringify({"sender": userId, "message": text});
    xhr.send(data);
}

/**
 * Handle the response from rasa, send each message to the Niceday user.
 **/
function handleRasaResponse() {
        if (this.readyState === 4 && this.status === 200) {
            var responseJson = JSON.parse(this.responseText);
            for (const message of responseJson) {
                chatSdk.sendTextMessage(parseInt(message.recipient_id), message.text).then(response => {
                    console.log("Successfully sent the message", response)});
            }
        } else if (this.readyState === 4) {
            console.log('Something went wrong, status:', this.status, this.responseText)
        }
    };

/**
 * Handle an incoming Niceday message
 **/
function handleIncomingMessage(message) {
  console.log(message);
  if (message.from !== THERAPIST_USER_ID && message.to === THERAPIST_USER_ID) {
      requestRasa(message.content.TEXT, message.from, handleRasaResponse)
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
