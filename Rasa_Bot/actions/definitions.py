"""
Stores definitions used in rasa actions, related to database, endpoints, timezone etcetera.
"""
import os
from enum import Enum

from dateutil import tz

# load database url and niceday_api_endopint variables
DATABASE_URL = os.getenv('DATABASE_URL')
NICEDAY_API_ENDPOINT = os.getenv('NICEDAY_API_ENDPOINT')

# Timezone for saving data to database
TIMEZONE = tz.gettz("Europe/Amsterdam")

REDIS_URL = os.getenv('REDIS_URL')

MORNING = (6, 12)
AFTERNOON = (12, 18)
EVENING = (18, 24)

# number of activities displayed by the first aid kit
NUM_TOP_ACTIVITIES = 5