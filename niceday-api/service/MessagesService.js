'use strict';

var goalieJs = require('@sense-os/goalie-js')
var Chat = goalieJs.Chat
var SenseServerEnvironment = goalieJs.SenseServerEnvironment
var ConnectionStatus = goalieJs.ConnectionStatus
//import { Chat, SenseServerEnvironment, ConnectionStatus } from '@sense-os/goalie-js';

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

    var userId = 38714
    var token = 'e74f99d4131e9a525140f1ccd100fc834ae5b90c7e60f128b3a2f7cfa5e3adeb'
    chatSdk.connect(userId, token)

    chatSdk.subscribeToConnectionStatusChanges((connectionStatus) => {
        if (connectionStatus === ConnectionStatus.Connected) {
        chatSdk.sendInitialPresence();
        chatSdk.sendTextMessage(body.recipient_id, body.text).then(response => {
            console.log("Succesfully sent the message", response)
        })}
    });
    resolve();
  });
}

