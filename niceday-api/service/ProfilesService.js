const goalieJs = require('@sense-os/goalie-js');

const { SenseServer } = goalieJs
const { Profile } = goalieJs
require('isomorphic-fetch')

// Read in environment variables from .env file
require('dotenv').config();

const THERAPIST_USER_ID = parseInt(process.env.THERAPIST_USER_ID, 10);
const TOKEN = process.env.NICEDAY_TOKEN;

const userProfile = new Profile(SenseServer.Alpha);

exports.getUserProfile = function (userId) {

  return new Promise((resolve, reject) => { // eslint-disable-line no-unused-vars

    userProfile
        .getUserDataById(TOKEN, userId)
        .then(result => {
            console.log('Result:', result)
            resolve(result);
        })
        .catch(err => {
            console.log('Error:', err);
            reject(err);
        });
  });
};
