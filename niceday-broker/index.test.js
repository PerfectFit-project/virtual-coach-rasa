const MOCK_ID_FROM = 1;
const MOCK_ID_TO = 12345;
const MOCK_TEST_MESSAGE = 'Test message';
const MOCK_TOKEN = 'mocktoken';

describe('Test niceday-broker with mocked Rasa and goaliejs', () => {

  it('Test message Niceday->Broker->Rasa', () => {

    // Mock the Authentication and Chat classes of goaliejs
    jest.mock('@sense-os/goalie-js', () => ({
      SenseServer: () => ({
        Alpha: undefined,
      }),
      SenseServerEnvironment: () => ({
        Alpha: undefined,
      }),
      Authentication: jest.fn().mockImplementation(() => ({
        login: () => new Promise((resolve) => {
          console.debug('Mocking successful authentication');
          const mockAuthResponse = {
            token: MOCK_TOKEN,
            user: {
              id: MOCK_ID_TO,
            },
          };
          resolve(mockAuthResponse);
        }),
      })),
      Chat: jest.fn().mockImplementation(() => ({
        init: jest.fn(),
        connect: jest.fn(),
        subscribeToConnectionStatusChanges: jest.fn(),
        sendInitialPresence: jest.fn(),
        subscribeToIncomingMessage: (handler) => {
          mockTestMessage = {
            from: MOCK_ID_FROM,
            to: MOCK_ID_TO,
            content: {
              TEXT: MOCK_TEST_MESSAGE,
            },
          };

          handler(mockTestMessage);
        },
      })),
    }));

    // Mock the XMLHttpRequest class (normally used to speak to Rasa bot)
    jest.mock('xmlhttprequest', () => ({
      XMLHttpRequest: jest.fn().mockImplementation(() => ({
        open: jest.fn(),
        setRequestHeader: jest.fn(),
        send: jest.fn(),
      })),
    }));


    // Set up the broker, with mocked message from the niceday server
    // received by the broker and passed on to Rasa. Does not yet test
    // onRasaResponse().

    const { setup } = require('./index'); // eslint-disable-line global-require
    setup(MOCK_ID_TO, MOCK_TOKEN);

  });
});
