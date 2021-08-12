const goalieJs = require('@sense-os/goalie-js');

const { Chat } = goalieJs;
const { SenseServerEnvironment } = goalieJs;
const { ConnectionStatus } = goalieJs;
const { XMLHttpRequest } = require('xmlhttprequest');

// Read in environment variables from .env file
require('dotenv').config();

const THERAPIST_USER_ID = parseInt(process.env.THERAPIST_USER_ID, 10);
const TOKEN = process.env.NICEDAY_TOKEN;
const { RASA_AGENT_URL } = process.env;

const chatSdk = new Chat();

/**
 * Request a response from rasa for a given text message
 * */
function requestRasa(text, userId, callback) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', RASA_AGENT_URL, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = callback;
  const data = JSON.stringify({ sender: userId, message: text });
  xhr.send(data);
}

/**
 * Handle the response from rasa, send each message to the Niceday user.
 * */
function handleRasaResponse() {
  if (this.readyState === 4 && this.status === 200) {
    const responseJson = JSON.parse(this.responseText);
    responseJson.forEach((message) => {
      chatSdk.sendTextMessage(parseInt(message.recipient_id, 10), message.text).then((response) => {
        console.log('Successfully sent the message', response);
      });
    });
  } else if (this.readyState === 4) {
    console.log('Something went wrong, status:', this.status, this.responseText);
  }
}

/**
 * Handle an incoming Niceday message
 * */
function handleIncomingMessage(message) {
  console.log(message);
  if (message.from !== THERAPIST_USER_ID && message.to === THERAPIST_USER_ID) {
    requestRasa(message.content.TEXT, message.from, handleRasaResponse);
  }
}

// Setup connection
chatSdk.init(SenseServerEnvironment.Alpha);
chatSdk.connect(THERAPIST_USER_ID, TOKEN);

// Send initial presence when connected
chatSdk.subscribeToConnectionStatusChanges((connectionStatus) => {
  if (connectionStatus === ConnectionStatus.Connected) {
    chatSdk.sendInitialPresence();
  }
});
console.log('Listening to incoming message...');
chatSdk.subscribeToIncomingMessage(handleIncomingMessage);
