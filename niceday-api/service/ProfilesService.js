const { SenseNetwork, SenseServer } = require('@sense-os/goalie-js');
require('isomorphic-fetch');

const userNetwork = new SenseNetwork(SenseServer.Alpha);

/**
 * Fetch the user profile corresponding to the given user ID.
 *
 * @param req - The node.js express request object
 * @param req - The node.js express body object
 *
 * Returns the profile as JSON.
 * */
exports.getUserProfile = (req, body) => new Promise((resolve, reject) => {
  userNetwork
    .getContact(req.app.get('token'), body)
    .then((result) => {
      console.log('Result:', result);
      resolve(result);
    })
    .catch((err) => {
      console.log('Error:', err);
      reject(err);
    });
});
