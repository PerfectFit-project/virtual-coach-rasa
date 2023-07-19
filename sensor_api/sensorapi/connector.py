import jwt
import logging
import os
import requests
import pandas as pd
import numpy as np
from datetime import timedelta, date, datetime
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

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
MIN_VALUE_STEP_GOAL = 2000
MAX_VALUE_STEP_GOAL = 10000
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
                   start_date: Optional[date] = None,
                   end_date: Optional[date] = None) -> Optional[List[Dict[Any, Any]]]:
    """
    Get the steps data of a user in the specified time interval.
    Args:
        user_id (int): ID of the user whom data needs to be queried.
        start_date (Optional[date]): start of the range of days to query. This day is  included in
                                     the interval.
        end_date (Optional[date]): end of the range of days to query. This day is not included in
                                   the interval.

    Returns: A list of dictionary containing, for each day, the date and the number of steps. If no
    start or end date is specified, it will return all available step data.
    """

    token = get_jwt_token(user_id)
    headers = {TOKEN_HEADER: token}

    if start_date is not None and end_date is not None:
        query_params = {'start': start_date.strftime("%Y-%m-%d"),
                        'end': end_date.strftime("%Y-%m-%d")}

        res = requests.get(STEPS_URL, params=query_params, headers=headers, timeout=60)

    else:
        res = requests.get(STEPS_URL, headers=headers, timeout=60)

    try:
        res_json = res.json()
        mapped_results = [{'date': format_sensors_date(day['localTime']), 'steps': day['value']}
                          for day in res_json]

        return mapped_results

    except ValueError:
        logging.error(f"Error in returned value from sensors: '{res}'")
        return []


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

    query_params = {'start': start_date.strftime("%Y-%m-%d"),
                    'end': end_date.strftime("%Y-%m-%d")}

    headers = {TOKEN_HEADER: token}

    res = requests.get(HR_URL, params=query_params, headers=headers, timeout=60)

    try:
        res_json = res.json()
        intensity_minutes = 0
        for hour in res_json:
            intensity_minutes += sum(val > HR_INTENSITY_THRESHOLD for val in hour['values'])

        return intensity_minutes

    except ValueError:
        logging.error(f"Error in returned value from sensors: '{res}'")
        return None


def get_step_goals_and_steps(steps_data: Optional[List[Dict[Any, Any]]],
                             start: datetime,
                             end: datetime) -> Tuple[Optional[List[int]],
                                                     Optional[List[int]],
                                                     Optional[List[str]],
                                                     Optional[int]]:
    """
    Calculate step goals for consecutive 9-day periods within a specified date range and the actual
    steps corresponding to the goals. Also, a list with the dates of these steps is returned. Lastly,
    the option is to return the value of the amount of days that the step goal was achieved.

    Args:
        steps_data (list): List of dictionaries containing 'date' and 'steps' data.
        start (datetime.datetime): Start date of the desired range.
        end (datetime.datetime): End date of the desired range.

    Returns:
        goals (list): List of step goals calculated for each consecutive 9-day period within the
                      specified range.
        actual_steps (list): List of actual taken steps from the last 7 days before the specified
                             end date. Missing values are returned as 0.
        date_list (list): List of dates corresponding to the values in 'actual_steps'.
        goals_achieved (int): number of days that the step goals were reached
    """

    if len(steps_data) == 0:  # No data is returned from db
        return None, None, None, None

    df = pd.DataFrame(steps_data)
    df.set_index('date', inplace=True)

    # Check whether the first expected date is present
    if df.index.min().strftime('%y%m%d') != start.strftime('%y%m%d'):
        df.loc[start.date()] = np.nan

    # Check whether last expected date is present
    end_date = end - timedelta(days=1)  # -1 day, because the end date is not returned from the API
    if df.index.max().strftime('%y%m%d') != end_date.strftime('%y%m%d'):
        df.loc[end_date.date()] = np.nan

    # Resample the data to a day-to-day basis. Add nans for empty dates
    df = df.asfreq('D')

    # Calculate the step goals
    steps = list(df.steps)
    step_goals = []
    for i in range(7):
        steps_nine_days = steps[i:i + 9]
        steps_nine_days = [x for x in steps_nine_days if not pd.isna(x)]  # Remove NaN values

        for _ in range(9 - len(steps_nine_days)):
            steps_nine_days.append(np.mean(steps_nine_days))  # Add the avg value up to 9 values

        steps_nine_days.sort()
        step_goals.append(int(round(steps_nine_days[5], -1)))  # Definition of the goal

    # Minimum goal is 2000, max is 10.000 steps/per day.
    step_goals = min_max_step_goal(step_goals)

    actual_steps = [int(x) if not np.isnan(x) else 0 for x in steps[-7:]]

    # Calculate number of days goal is achieved
    goals_achieved = sum(np.array(step_goals) < np.array(actual_steps))

    # Get list with dates
    date_list = df.index[-7:]
    date_list = date_list.strftime('%a %d').tolist()  # Convert the dates to the desired format

    return step_goals, actual_steps, date_list, goals_achieved


def get_daily_step_goal_from_db(user_id) -> Optional[int]:
    """
    Get daily step goal for a given user using data from the step count database.

    For example, for a single participant, daily step count over the last 9 days (ranked from
    lowest to highest) was 1250, 1332, 3136, 5431, 5552, 5890, 6402, 7301, 10,103. In this case,
    the 60th percentile represents a goal of 5890 steps. The 6th element is used.

    If there is not data for 9 days available, the number of days will be supplemented to 9 by
    adding the average of the days with data.

    Args:
    user_id (int): The user ID for whom the daily step goal is to be retrieved from the database.

    Returns:
    int: The daily step goal for the given user, retrieved from the database.
    """
    steps_per_day = []

    end = datetime.now()
    start = end - timedelta(days=9)
    steps_data = get_steps_data(user_id=user_id, start_date=start, end_date=end)

    if len(steps_data) == 0:  # do something if steps_data is empty
        return None

    for day in steps_data:
        steps_per_day.append(day['steps'])

    for _ in range(9 - len(steps_per_day)):
        steps_per_day.append(np.mean(steps_per_day))  # Add with the avg value up to 9 values

    steps_per_day.sort()
    pa_goal = int(round(steps_per_day[5], -1))

    # Min value 2000, max value 10.000
    pa_goal = min_max_step_goal(pa_goal)
    return pa_goal


def min_max_step_goal(step_goal):
    """
    Applies a minimum, maximum, and step goal transformation to the input value(s).

    Parameters:
        step_goal (int, float, list): The input value(s) to be transformed. It can be a single
                                      value or a list of values.

    Returns:
        int, float, list: If `pa_goal` is a single value, the function returns the transformed
                          value according to the minimum and maximum bounds. If `pa_goal` is a
                          list of values, the function returns a list of transformed values
    """
    if isinstance(step_goal, list):
        return [min(max(x, MIN_VALUE_STEP_GOAL), MAX_VALUE_STEP_GOAL) for x in step_goal]

    return min(max(step_goal, MIN_VALUE_STEP_GOAL), MAX_VALUE_STEP_GOAL)
