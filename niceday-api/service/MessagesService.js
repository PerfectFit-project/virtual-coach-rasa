const { Chat, SenseServerEnvironment, ConnectionStatus } = require('@sense-os/goalie-js');

/**
 * Send a text message
 *
 * @param req - The node.js express request object
 * @param req - The node.js express body object
 *
 * no response value expected for this operation
 * */
exports.sendTextMessage = function (req, body) {
  return new Promise((resolve, reject) => { // eslint-disable-line no-unused-vars
    const chatSdk = new Chat();
    chatSdk.init(SenseServerEnvironment.Alpha);
    chatSdk.connect(req.app.get('therapistId'), req.app.get('token'));

    const subscriptionId = chatSdk.subscribeToConnectionStatusChanges((connectionStatus) => {
      if (connectionStatus === ConnectionStatus.Connected) {
        chatSdk.sendInitialPresence();
        chatSdk.sendTextMessage(body.recipient_id, body.text).then((response) => {
          console.log('Successfully sent the message', response);
          chatSdk.unsubscribeFromConnectionStatusChanges(subscriptionId);
        });
      }
    });
    resolve();
  });
};
