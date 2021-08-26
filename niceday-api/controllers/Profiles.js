const utils = require('../utils/writer.jsx');
const Profiles = require('../service/ProfilesService');

module.exports.getUserProfile = function getUserProfile(req, res, next, body) {
  Profiles.getUserProfile(req, body)
    .then((response) => {
      utils.writeJson(res, response);
    })
    .catch((response) => {
      utils.writeJson(res, response);
    });
};
