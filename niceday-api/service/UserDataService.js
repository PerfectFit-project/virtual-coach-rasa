const { SenseNetwork, SenseServer } = require('@sense-os/goalie-js');
require('isomorphic-fetch');

const userNetwork = new SenseNetwork(SenseServer.Alpha);

/**
 * Fetch the user data corresponding to the given user ID.
 * Returns the JSON as received from the SenseServer.
 * */
exports.getUserData = (userId) => new Promise((resolve, reject) => {
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
