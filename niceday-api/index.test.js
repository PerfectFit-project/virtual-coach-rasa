require('isomorphic-fetch');
const http = require('http');
const {create_niceday_api_server} = require('./index.js');

const NICEDAY_TEST_SERVERPORT = 8080;
const NICEDAY_TEST_USER_ID = 38527;

describe('Test fetching of user data', () => {
  beforeAll(() => {
    jest.mock('@sense-os/goalie-js');
  });

  beforeEach((done) => {
    jest.mock('@sense-os/goalie-js');
    server = create_niceday_api_server();
    server.listen(NICEDAY_TEST_SERVERPORT, () => {
      console.debug('Test server up and listening on port %d', NICEDAY_TEST_SERVERPORT);
      done();
    });
  });

  afterEach((done) => {
   console.debug('Stopping server');
   server.close(done);
  });

  it('Mock Test Case', () => {
    return fetch('http://localhost:8080/userdata/' + NICEDAY_TEST_USER_ID)
    .then(function(response) {
        console.log(response);
    });
  });
});
