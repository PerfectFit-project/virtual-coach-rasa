const { CustomTrackers, SenseServer } = require('@sense-os/goalie-js');
require('isomorphic-fetch');

const customTrackerSdk = new CustomTrackers(SenseServer.Alpha);

/**
 * Set user tracker status.
 * @param req - The node.js express request object
 * @param body - The node.js express body object.
 * */
exports.setUserTrackerStatuses = (req, body) => new Promise((resolve, reject) => {
  const { userId, trackerStatuses } = body;
  customTrackerSdk
    .postUserTrackerStatus(req.app.get('token'), userId, trackerStatuses)
    .then((result) => {
      console.log('Result:', result);
      resolve(result);
    })
    .catch((err) => {
      console.log('Error:', err);
      reject(err);
    });
});
