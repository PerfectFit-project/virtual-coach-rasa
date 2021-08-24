const utils = require('../utils/writer.jsx');
const UserData = require('../service/UserDataService');

module.exports.getUserData = function getUserData(req, res, next, body) {
  UserData.getUserData(body)
    .then((response) => {
      utils.writeJson(res, response);
    })
    .catch((response) => {
      utils.writeJson(res, response);
    });
};
