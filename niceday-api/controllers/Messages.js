'use strict';

var utils = require('../utils/writer.js');
var Messages = require('../service/MessagesService');

module.exports.sendTextMessage = function sendTextMessage (req, res, next, body) {
  Messages.sendTextMessage(body)
    .then(function (response) {
      utils.writeJson(res, response);
    })
    .catch(function (response) {
      utils.writeJson(res, response);
    });
};
