import requests


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

        return results

    def get_profile(self, user_id) -> dict:
        """
        Returns the niceday user data corresponding to the given user id.
        This is in the form of a dict, containing the user's
            'networks' (memberId, role etc)
            'userProfile' (name, location, bio, birthdate etc)
            'user' info (username, email, date joined etc.)
        The exact contents of this returned data depends on what is stored
        on the SenseServer.
        """

        endpoint = 'profiles'
        query_params = []
        path_param = str(user_id)
        return self._niceday_api(endpoint, query_params, path_param)
