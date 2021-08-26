import requests

from niceday_client.definitions import USER_PROFILE_KEYS

class NicedayClient:
    """
    Client for interacting with the niceday-api component of the PerfectFit
    stack.
    """

    def __init__(self, niceday_api_uri='http://localhost:8080/'):
        """
        Construct a client for interacting with the given niceday API URI.
        By default, this is assumed to be on http://localhost:8080/, but
        can be set with the niceday_api_uri parameter.
        """

        self._niceday_api_uri = niceday_api_uri

    def _niceday_api(self,
                     endpoint: str,
                     query_params: dict,
                     path_param: str) -> dict:
        """
        Handles http requests with the niceday-api.

        endpoint: str
            Specifies the desired endpoint e.g. 'profiles' or 'messages'

        query_params: dict
            Parameters that should go in the query string of the request URL

        path_param: str
            The parameter that goes at the end of the path.
            i.e. [nice-day-api-url]/endpoint/path_param
        """

        if not endpoint.endswith('/'):
            endpoint += '/'

        headers = {"Accept": "application/json"}
        url = self._niceday_api_uri + endpoint + path_param
        r = requests.get(url, params=query_params, headers=headers)
        r.raise_for_status()

        try:
            results = r.json()
        except ValueError as e:
            raise ValueError('The niceday-api did not return JSON.') from e

        self.error_check(results, 'Unauthorized error')
        self.error_check(results, 'The requested resource could not be found')

        return results

    def error_check(self, results, err_msg):
        if 'message' in results:
            if err_msg in results['message']:
                msg = f"'{err_msg}' response from niceday server. "
                if 'details' in results:
                    if 'body' in results['details']:
                        msg += 'Details provided: ' + str(results['details']['body'])
                raise Exception(msg)

    def _get_raw_user_data(self, user_id) -> dict:
        """
        Returns the niceday user data corresponding to the given user id.
        This is in the form of a dict, containing the user's
            'networks' (memberId, role etc)
            'userProfile' (name, location, bio, birthdate etc)
            'user' info (username, email, date joined etc.)
        The exact contents of this returned data depends on what is stored
        on the SenseServer and generally could change (beyond our control).
        """
        endpoint = 'userdata'
        query_params = {}
        path_param = str(user_id)
        return self._niceday_api(endpoint, query_params, path_param)

    def get_profile(self, user_id) -> dict:
        """
        Returns the niceday user profile corresponding to the given user id.
        This is in the form of dict, containing the following keys:
            'networks' (memberId, role etc)
            'userProfile' (name, location, bio, birthdate etc)
            'user' info (username, email, date joined etc.)
        The exact contents of this returned data depends on what is stored
        on the SenseServer.
        """

        user_data = self._get_raw_user_data(user_id)
        if 'userProfile' not in user_data:
            raise ValueError('NicedayClient expected user data from '
                             'niceday-api to contain the key "userProfile" '
                             'but this is missing. Has the data structure '
                             'stored on the Senseserver changed?')

        return_profile = {}
        for k in USER_PROFILE_KEYS:
            if k not in user_data['userProfile']:
                raise ValueError(f'"userProfile" dict returned from '
                                 f'niceday-api does not contain expected '
                                 f'key "{k}". Has the data structure '
                                 f'stored on the Senseserver changed?')
            return_profile[k] = user_data['userProfile'][k]

        return return_profile
