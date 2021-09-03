require('isomorphic-fetch');

const NICEDAY_TEST_SERVERPORT = 8080;
const NICEDAY_TEST_USER_ID = 38527;
const MOCK_USER_DATA = {
  id: NICEDAY_TEST_USER_ID,
  userProfile: {
    firstName: 'Mr Mock',
  },
};

// Contains all tests which require a mocked Senseserver
describe('Tests on niceday-api server using mocked goalie-js', () => {
  let server;

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
        Alpha: undefined,
      }),
      SenseNetwork: jest.fn().mockImplementation(() => ({
        getContact: () => new Promise((resolve) => {
          resolve(MOCK_USER_DATA);
        }),
      })),
      Authentication: jest.fn().mockImplementation(() => ({
        login: () => new Promise((resolve) => {
          console.debug('Mocking successful authentication');
          const mockAuthResponse = {
            token: 'mocktoken',
            user: {
              id: 12345,
            },
          };
          resolve(mockAuthResponse);
        }),
      })),
    }));
  });

  // Set up - start niceday-api REST server (and wait until it is ready)
  beforeEach((done) => {
    const { createNicedayApiServer } = require('./index'); // eslint-disable-line global-require
    server = createNicedayApiServer();
    server.listen(NICEDAY_TEST_SERVERPORT, () => {
      console.debug('Test server up and listening on port %d', NICEDAY_TEST_SERVERPORT);
      done();
    });
  });

  // Tear down - stop niceday-api REST server after each test
  afterEach((done) => {
    console.debug('Stopping server');
    server.close(done);
  });

  it('Test fetching user data from userdata/ endpoint', () => {
    /*
      Sends a GET to the /userdata/ endpoint and checks that the expected
      (mock) user data is returned.
    */

    const urlreq = `http://localhost:${NICEDAY_TEST_SERVERPORT}/userdata/${NICEDAY_TEST_USER_ID}`;
    return fetch(urlreq)
      .then((response) => response.json())
      .then((responseBody) => {
        expect(responseBody).toEqual(MOCK_USER_DATA);
      })
      .catch((error) => {
        throw new Error(`Error during fetch: ${error}`);
      });
  });
});
