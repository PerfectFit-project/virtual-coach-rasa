import jwt
import logging
import os
import requests

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# dev or prod environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# information for reading sensors data
SENSOR_KEY_PATH = '/app/sensorprivatekey'

if ENVIRONMENT == 'prod':
    # TODO: replace with actual url when this will be made available
    API_URL = 'https://portal.rrdweb.nl/servlets/r2d2/v6.0.4/project/perfectfit/'
else:
    # TODO: replace with actual url when this will be made available
    API_URL = 'https://www.rrdhost.nl/servlets/senseeact/v6.0.4/project/perfectfit/'

STEPS_URL = API_URL + 'table/garmin_steps_day'
HR_URL = API_URL + 'table/garmin_heart_history'
HR_INTENSITY_THRESHOLD = 110

TOKEN_HEADER = 'X-PerfectFit-Auth-Token'


# functions for sensors data querying
def get_jwt_token(user_id: int) -> str:
    """
    Get the encoded JWT token for querying the sensors' data.
    Args:
        user_id: ID of the user whom data needs to be queried.

    Returns: the encoded JWD token

    """

    with open(SENSOR_KEY_PATH, 'rb') as f:
        private_key = serialization.load_ssh_private_key(
            f.read(), password=None, backend=default_backend()
        )

    encoded = jwt.encode({"sub": user_id, "iat": int(round(datetime.now().timestamp()))},
                         private_key, algorithm="RS256")

    return encoded


# functions for sensors data querying
def get_steps_data(user_id: int,
                   start_date: date,
                   end_date: date) -> Optional[List[Dict[Any, Any]]]:
    """
    Get the steps data of a user in the specified time interval.
    Args:
        user_id: ID of the user whom data needs to be queried.
        start_date: start of the range of days to query. This day is included in the interval.
        end_date: end of the range of days to query. This day is not included in the interval.

    Returns: A list of dictionary containing, for each day, the date and the number of steps.
    """

    token = get_jwt_token(user_id)

    query_params = {'start': start_date.strftime("%Y-%m-%dT%X"),
                    'end': end_date.strftime("%Y-%m-%dT%X")}

    headers = {TOKEN_HEADER: token}

    res = requests.get(STEPS_URL, params=query_params, headers=headers, timeout=60)

    try:
        res_json = res.json()
        mapped_results = [{'date': format_sensors_date(day['localTime']), 'steps': day['value']}
                          for day in res_json]

        return mapped_results

    except ValueError:
        logging.error('Error in returned value from sensors')
        return None


def format_sensors_date(sensors_date: str) -> date:
    """
    Convert the time format returned by the sensors data into date format.
    Args:
        sensors_date: time value returned by sensors' data.

    Returns: The formatted date.

    """

    original_format = '%Y-%m-%dT%H:%M:%S.%f'

    formatted_date = datetime.strptime(sensors_date, original_format).date()

    return formatted_date


def get_intensity_minutes_data(user_id: int,
                               start_date: date,
                               end_date: date) -> Optional[int]:
    """
    Retrieves the intensity minutes data for a specific user within a given date range.

    Args:
        user_id (int): The ID of the user.
        start_date (date): The start date of the data range.
        end_date (date): The end date of the data range.

    Returns:
        Optional[int]: The total number of intensity minutes recorded during the specified
        date range. Returns None if there was an error in retrieving or processing the data.
    """

    token = get_jwt_token(user_id)

    query_params = {'start': start_date.strftime("%Y-%m-%dT%X"),
                    'end': end_date.strftime("%Y-%m-%dT%X")}

    headers = {TOKEN_HEADER: token}

    res = requests.get(HR_URL, params=query_params, headers=headers, timeout=60)

    try:
        res_json = res.json()
        intensity_minutes = 0
        for hour in res_json:
            intensity_minutes += sum(val > HR_INTENSITY_THRESHOLD for val in hour['values'])

        return intensity_minutes

    except ValueError:
        logging.error('Error in returned value from sensors')
        return None
