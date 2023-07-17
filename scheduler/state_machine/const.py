import os
from dateutil import tz

# maximum duration of the dialog in seconds
MAXIMUM_DIALOG_DURATION = 90*60
# maximum number of days of inactivity before sending a notification
MAXIMUM_INACTIVE_DAYS = 10

# time interval in seconds for checking for new connection requests
INVITES_CHECK_INTERVAL = 10*60

# next message is delivered
WORDS_PER_SECOND = 5
# maximum delay, in seconds, between a message and the next one
MAX_DELAY = 10

# PA groups
LOW_PA_GROUP = 1
HIGH_PA_GROUP = 2

# duration in weeks
EXECUTION_DURATION_WEEKS = os.getenv('EXECUTION_DURATION_WEEKS')

# intervention times (days)
ACTIVITY_C2_9_DAY_TRIGGER = os.getenv('ACTIVITY_C2_9_DAY_TRIGGER')
FUTURE_SELF_INTRO = os.getenv('FUTURE_SELF_INTRO')
GOAL_SETTING = os.getenv('GOAL_SETTING')
# number of days after the weekly reflection for the PA notification to be sent
TIME_DELTA_PA_NOTIFICATION = os.getenv('TIME_DELTA_PA_NOTIFICATION')
TRACKING_DURATION = os.getenv('TRACKING_DURATION')
PREPARATION_GA = os.getenv('PREPARATION_GA')
MAX_PREPARATION_DURATION = os.getenv('MAX_PREPARATION_DURATION')
EXECUTION_DURATION = EXECUTION_DURATION_WEEKS * 7  # 12 weeks
#

REDIS_URL = os.getenv('REDIS_URL')
ENVIRONMENT = os.getenv('ENVIRONMENT')
DATABASE_URL = os.getenv('DATABASE_URL')
NICEDAY_API_ENDPOINT = os.getenv('NICEDAY_API_ENDPOINT')
TRIGGER_COMPONENT = 'celery_tasks.trigger_intervention_component'
SCHEDULE_TRIGGER_COMPONENT = 'celery_tasks.trigger_scheduled_intervention_component'
TRIGGER_INTENT = 'celery_tasks.trigger_intent'
TIMEZONE = tz.gettz("Europe/Amsterdam")

# dialog states definitions
NOT_RUNNING = 0
RUNNING = 1
EXPIRED = 2
NOTIFY = 3
