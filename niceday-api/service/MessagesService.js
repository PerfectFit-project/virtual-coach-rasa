'use strict';

var goalieJs = require('@sense-os/goalie-js')
var Chat = goalieJs.Chat
var SenseServerEnvironment = goalieJs.SenseServerEnvironment
var ConnectionStatus = goalieJs.ConnectionStatus

//Read in environment variables from .env file
require('dotenv').config()
const THERAPIST_USER_ID = parseInt(process.env.THERAPIST_USER_ID)
const TOKEN = process.env.NICEDAY_TOKEN

/**
 * Send a text message
 *
 * body Message  (optional)
 * no response value expected for this operation
 **/
exports.sendTextMessage = function(body) {
  return new Promise(function(resolve, reject) {
    const chatSdk = new Chat();
    chatSdk.init(SenseServerEnvironment.Alpha);

    chatSdk.connect(THERAPIST_USER_ID, TOKEN)

    chatSdk.subscribeToConnectionStatusChanges((connectionStatus) => {
        if (connectionStatus === ConnectionStatus.Connected) {
        chatSdk.sendInitialPresence();
        chatSdk.sendTextMessage(body.recipient_id, body.text).then(response => {
            console.log("Successfully sent the message", response)
        })}
    });
    resolve();
  });
}

