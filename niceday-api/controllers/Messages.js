const utils = require('../utils/writer.jsx');
const Messages = require('../service/MessagesService');

module.exports.sendTextMessage = function sendTextMessage(req, res, next, body) {
  Messages.sendTextMessage(body)
    .then((response) => {
      utils.writeJson(res, response);
    })
    .catch((response) => {
      utils.writeJson(res, response);
    });
};
