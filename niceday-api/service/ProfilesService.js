const goalieJs = require('@sense-os/goalie-js');

const { SenseNetwork, SenseServer } = goalieJs;
const userNetwork = new SenseNetwork(SenseServer.Alpha);

require('isomorphic-fetch');

// Read in environment variables from .env file
require('dotenv').config();

const TOKEN = process.env.NICEDAY_TOKEN;

/**
 * Fetch the user profile corresponding to the given user ID.
 * Returns the profile as JSON.
 * */
exports.getUserProfile = (userId) => new Promise((resolve, reject) => {
  userNetwork
    .getContact(TOKEN, userId)
    .then((result) => {
      console.log('Result:', result);
      resolve(result);
    })
    .catch((err) => {
      console.log('Error:', err);
      reject(err);
    });
});
