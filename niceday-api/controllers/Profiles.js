const utils = require('../utils/writer.jsx');

module.exports.getUserProfileById = function getUserProfile(req, res, next, body) {
    response = {'profile': 'test'};
    utils.writeJson(res, response);
};
