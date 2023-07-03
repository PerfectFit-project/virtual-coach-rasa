import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import secrets
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import jwt

from Rasa_Bot.actions.definitions import (AFTERNOON_SEND_TIME,
                          DATABASE_URL,
                          EVENING_SEND_TIME,
                          SENSOR_KEY_PATH,
                          MORNING_SEND_TIME,
                          NUM_TOP_ACTIVITIES,
                          PROFILE_CREATION_CONF_SLOTS,
                          STEPS_URL,
                          TIMEZONE,
                          TOKEN_HEADER,
                          FsmStates)


# functions for sensors data querying
def get_jwt_token(user_id: int) -> str:
    """
    Get the encoded JWT token for querying the sensors' data.
    Args:
        user_id: ID of the user whom data needs to be queried.

    Returns: the encoded JWD token

    """

    with open(r"C:\Users\bscheltinga\OneDrive - University of Twente\Documents\virtual-coach-main\rrd_testenv", 'rb') as f:
        private_key = serialization.load_ssh_private_key(
            f.read(), password=b"WaBac789$", backend=default_backend()
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

    query_params = {'start': start,
                    'end': end}

    headers = {TOKEN_HEADER: token}

    res = requests.get(STEPS_URL, params=query_params, headers=headers, timeout=60)

    try:
        res_json = res.json()
        mapped_results = [{'date': format_sensors_date(day['localTime']), 'steps': day['value']}
                          for day in res_json]

        return mapped_results

    except ValueError:
        logging.error(f"Error in returned value from sensors: '{res}'")
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

id = 43895
start = datetime(2023, 4, 15)
start = start.strftime("%Y-%m-%dT%X")
end = datetime(2023, 4, 19)
end = end.strftime("%Y-%m-%dT%X")

num_steps = get_steps_data(43895, start, end)