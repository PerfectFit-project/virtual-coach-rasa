describe('Test niceday-broker with mocked Rasa and goaliejs', () => {

  beforeAll(() => {

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
            token: 'mocktoken',
            user: {
              id: 12345,
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
            from: 1,
            to: 12345,
            content: {
              TEXT: 'Test message',
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

  });

  it('Test all functions', () => {
    const { setup } = require('./index'); // eslint-disable-line global-require
    setup(12345, 'mocktoken');
  });
});
