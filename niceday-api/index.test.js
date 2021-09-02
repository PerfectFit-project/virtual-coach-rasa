require('isomorphic-fetch');
const http = require('http');
const {create_niceday_api_server} = require('./index.js');

const NICEDAY_TEST_SERVERPORT = 8080;
const NICEDAY_TEST_USER_ID = 38527;
const MOCK_USER_DATA = { id: NICEDAY_TEST_USER_ID, userProfile: {'firstName': 'Mr Mock'}};


describe('Tests on niceday-api server using mocked goalie-js', () => {

  beforeAll(() => {


    // Mock the constructor of the SenseNetwork submodule of goaliejs to return
    // a mock with the getContact() method, which itself returns a promise containing
    // the MOCK_USER_DATA. SenseServer.Alpha needs to be mocked too since it is used
    // in calls to the constructor.
    //
    // More comprehensive documentation can be found here:
    // https://en.wikipedia.org/wiki/Lovecraftian_horror
    jest.mock('@sense-os/goalie-js', () => ({
      SenseServer: () => ({
        Alpha: undefined
      }),
      SenseNetwork: jest.fn().mockImplementation(() => {
        return { getContact: (token, body) => {
            return new Promise ((resolve, reject) => {
              resolve(MOCK_USER_DATA);
            });
          }
        };
      })
    }));


  });

  beforeEach((done) => {
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

  it('Test fetching user data from userdata/ endpoint', () => {

    return fetch('http://localhost:' + NICEDAY_TEST_SERVERPORT + '/userdata/' + NICEDAY_TEST_USER_ID)
      .then(response => response.json())
      .then(response_body =>{
        expect(response_body).toEqual(MOCK_USER_DATA);
      });
  });
});
