import requests

class NicedayClient:

    def __init__(self, niceday_api_uri='http://localhost:8080/'):
        self._niceday_api_uri = niceday_api_uri

    def _niceday_api(self, endpoint: str, query_params: dict, path_param: str) -> dict:
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
        endpoint = 'profiles'
        query_params = []
        path_param = str(user_id)
        return self._niceday_api(endpoint, query_params, path_param)
