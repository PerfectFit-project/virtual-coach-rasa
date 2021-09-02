require('isomorphic-fetch');
const http = require('http');
const {create_niceday_api_server} = require('./index.js');

const SERVERPORT = 8080;

describe('Test fetching of user data', () => {
  beforeEach((done) => {
    server = create_niceday_api_server();
    server.listen(SERVERPORT, () => {
      console.debug('Test server up and listening on port %d', SERVERPORT);
      done();
    });
  });

  afterEach((done) => {
   console.debug('Stopping server');
   server.close(done);
  });

  it('Mock Test Case', () => {
//    return fetch('http://localhost:8080/userdata/5218')
//    .then(function(response) {
//        console.log(response);
//    });
  });
});
