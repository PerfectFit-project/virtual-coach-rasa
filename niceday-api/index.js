const { Authentication, SenseServer } = require('@sense-os/goalie-js');
const path = require('path');
const http = require('http');
const oas3Tools = require('oas3-tools');
require('isomorphic-fetch');

const serverPort = 8080;

function create_niceday_api_server() {

  // Read in environment variables from .env file
  require('dotenv').config();

  const { THERAPIST_PASSWORD, THERAPIST_EMAIL_ADDRESS } = process.env;

  const authSdk = new Authentication(SenseServer.Alpha);

  // swaggerRouter configuration
  const options = {
    routing: {
      controllers: path.join(__dirname, './controllers'),
    },
  };

  const expressAppConfig = oas3Tools.expressAppConfig(path.join(__dirname, 'api/openapi.yaml'), options);
  const app = expressAppConfig.getApp();

  authSdk.login(THERAPIST_EMAIL_ADDRESS, THERAPIST_PASSWORD).then((response) => {
    app.set('therapistId', response.user.id);
    app.set('token', response.token);
  })
  .catch(error => {
    console.debug('Error during authentication:', error);
  });

  // Initialize the Swagger middleware
  var server = http.createServer(app);

  return server;
};

module.exports.create_niceday_api_server = create_niceday_api_server;

if (require.main === module) {

  server = create_niceday_api_server();

  server.listen(serverPort, () => {
    console.log('Your server is listening on port %d (http://localhost:%d)', serverPort, serverPort);
    console.log('Swagger-ui is available on http://localhost:%d/docs', serverPort);
  });
}


